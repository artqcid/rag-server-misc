"""CLI interface for RAG indexing."""
import asyncio
import logging
import sys
from pathlib import Path

import click

from .url_sets import URLSetManager
from .tier_runner import TierRunner
from .models import IndexingConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
def cli(verbose: bool):
    """RAG Indexing CLI - Index web content into Qdrant via RAG server."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)


@cli.command()
@click.option("--context", "-c", required=True, help="Context name (e.g., juce, vue, react)")
@click.option("--tier", "-t", help="Specific tier to index (e.g., tier1_overview)")
@click.option("--all-tiers", "-a", is_flag=True, help="Index all tiers")
@click.option("--collection", help="Override collection name")
@click.option("--dry-run", is_flag=True, help="Fetch and process without indexing")
@click.option("--rag-url", default="http://127.0.0.1:8002", help="RAG server URL")
def index(
    context: str,
    tier: str,
    all_tiers: bool,
    collection: str,
    dry_run: bool,
    rag_url: str,
):
    """Index content from a context into the RAG system."""
    if not tier and not all_tiers:
        click.echo("Error: Specify --tier or --all-tiers", err=True)
        sys.exit(1)
    
    url_manager = URLSetManager()
    runner = TierRunner(
        url_manager=url_manager,
        rag_server_url=rag_url,
    )
    
    async def run():
        if all_tiers:
            results = await runner.run_all_tiers(
                context,
                collection=collection,
                dry_run=dry_run,
            )
        else:
            results = [await runner.run_tier(
                context,
                tier,
                collection=collection,
                dry_run=dry_run,
            )]
        
        # Print results
        click.echo("\n" + "=" * 60)
        click.echo("INDEXING RESULTS")
        click.echo("=" * 60)
        
        total_docs = 0
        total_chunks = 0
        total_errors = 0
        
        for result in results:
            click.echo(f"\n{result.context}/{result.tier}:")
            click.echo(f"  URLs: {result.successful_fetches}/{result.total_urls} fetched")
            click.echo(f"  Documents: {result.documents_indexed}")
            click.echo(f"  Chunks: {result.chunks_created}")
            click.echo(f"  Duration: {result.duration_seconds:.1f}s")
            
            if result.errors:
                click.echo(f"  Errors: {len(result.errors)}")
                for err in result.errors[:3]:
                    click.echo(f"    - {err[:80]}...")
            
            total_docs += result.documents_indexed
            total_chunks += result.chunks_created
            total_errors += len(result.errors)
        
        click.echo("\n" + "-" * 60)
        click.echo(f"TOTAL: {total_docs} documents, {total_chunks} chunks, {total_errors} errors")
        
        if total_errors > 0:
            sys.exit(1)
    
    asyncio.run(run())


@cli.command("list-contexts")
def list_contexts():
    """List all available indexing contexts."""
    url_manager = URLSetManager()
    contexts = url_manager.list_contexts()
    
    if not contexts:
        click.echo("No contexts found.")
        click.echo(f"Add JSON files to: {url_manager.contexts_dir}")
        return
    
    click.echo("Available contexts:")
    click.echo("-" * 40)
    
    for name in contexts:
        info = url_manager.get_context_info(name)
        if info:
            click.echo(f"\n{name} ({info['library']})")
            click.echo(f"  Collection: {info['collection']}")
            click.echo(f"  Total URLs: {info['total_urls']}")
            click.echo(f"  Tiers:")
            for tier_name, tier_info in info['tiers'].items():
                click.echo(f"    - {tier_name}: {tier_info['url_count']} URLs ({tier_info['doc_type']})")


@cli.command("show")
@click.argument("context")
@click.option("--tier", "-t", help="Show specific tier")
@click.option("--urls", is_flag=True, help="Show all URLs")
def show(context: str, tier: str, urls: bool):
    """Show details about a context or tier."""
    url_manager = URLSetManager()
    ctx = url_manager.get_context(context)
    
    if not ctx:
        click.echo(f"Context '{context}' not found.", err=True)
        sys.exit(1)
    
    click.echo(f"Context: {ctx.context}")
    click.echo(f"Library: {ctx.library}")
    click.echo(f"Collection: {ctx.get_collection_name()}")
    
    if tier:
        tier_config = ctx.get_tier(tier)
        if not tier_config:
            click.echo(f"Tier '{tier}' not found.", err=True)
            sys.exit(1)
        
        click.echo(f"\nTier: {tier}")
        click.echo(f"  Description: {tier_config.description}")
        click.echo(f"  Source Type: {tier_config.source_type}")
        click.echo(f"  Doc Type: {tier_config.doc_type}")
        
        tier_urls = tier_config.get_urls()
        click.echo(f"  URL Count: {len(tier_urls)}")
        
        if urls:
            click.echo("\n  URLs:")
            for item in tier_urls:
                click.echo(f"    - {item['url']}")
    else:
        click.echo(f"\nTiers ({len(ctx.tiers)}):")
        for tier_name, tier_config in ctx.tiers.items():
            tier_urls = tier_config.get_urls()
            click.echo(f"  {tier_name}: {len(tier_urls)} URLs ({tier_config.doc_type})")
            click.echo(f"    {tier_config.description}")


@cli.command("verify")
@click.argument("context")
@click.option("--tier", "-t", help="Verify specific tier only")
@click.option("--limit", "-n", type=int, help="Max URLs to verify per tier (default: all)")
@click.option("--check-redirects", is_flag=True, help="Report 301/302 redirects")
def verify(context: str, tier: str, limit: int, check_redirects: bool):
    """Verify URLs are accessible and report issues."""
    import httpx
    
    url_manager = URLSetManager()
    ctx = url_manager.get_context(context)
    
    if not ctx:
        click.echo(f"Context '{context}' not found.", err=True)
        sys.exit(1)
    
    tiers_to_check = [tier] if tier else ctx.get_tier_names()
    
    total_urls = 0
    error_count = 0
    redirect_count = 0
    redirects_found = []
    errors_found = []
    
    async def check_urls():
        nonlocal total_urls, error_count, redirect_count
        
        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }
        ) as client:
            for tier_name in tiers_to_check:
                tier_config = ctx.get_tier(tier_name)
                if not tier_config:
                    continue
                
                tier_urls = tier_config.get_urls()
                urls_to_check = tier_urls[:limit] if limit else tier_urls
                
                click.echo(f"\n{tier_name} (checking {len(urls_to_check)} URLs):")
                
                for item in urls_to_check:
                    url = item["url"]
                    total_urls += 1
                    
                    try:
                        response = await client.get(url)
                        status = response.status_code
                        
                        # Check for redirects
                        if check_redirects and response.history:
                            for redirect in response.history:
                                if redirect.status_code in (301, 302, 307, 308):
                                    redirect_count += 1
                                    redirect_info = {
                                        "tier": tier_name,
                                        "original": url,
                                        "final": str(response.url),
                                        "status": redirect.status_code
                                    }
                                    redirects_found.append(redirect_info)
                                    click.echo(
                                        f"  ⚠ {redirect.status_code} REDIRECT: {url[:50]}... -> {str(response.url)[:50]}...",
                                        err=True
                                    )
                        
                        if status < 400:
                            if not (check_redirects and response.history):
                                click.echo(f"  ✓ {status} {url[:80]}...")
                        else:
                            error_count += 1
                            error_info = {
                                "tier": tier_name,
                                "url": url,
                                "status": status
                            }
                            errors_found.append(error_info)
                            click.echo(f"  ✗ {status} {url}", err=True)
                            
                    except Exception as e:
                        error_count += 1
                        error_info = {
                            "tier": tier_name,
                            "url": url,
                            "error": str(e)
                        }
                        errors_found.append(error_info)
                        click.echo(f"  ✗ ERROR: {url} - {e}", err=True)
    
    asyncio.run(check_urls())
    
    # Summary
    click.echo(f"\n{'='*80}")
    click.echo(f"SUMMARY for context '{context}':")
    click.echo(f"  Total URLs checked: {total_urls}")
    click.echo(f"  Errors: {error_count}")
    if check_redirects:
        click.echo(f"  Redirects (301/302): {redirect_count}")
    
    if errors_found:
        click.echo(f"\n{'='*80}")
        click.echo("ERRORS FOUND:")
        for err in errors_found:
            click.echo(f"  [{err['tier']}] {err['url']}")
            if 'status' in err:
                click.echo(f"    Status: {err['status']}")
            if 'error' in err:
                click.echo(f"    Error: {err['error']}")
    
    if check_redirects and redirects_found:
        click.echo(f"\n{'='*80}")
        click.echo("REDIRECTS FOUND (update these URLs):")
        for redir in redirects_found:
            click.echo(f"  [{redir['tier']}] {redir['status']}")
            click.echo(f"    OLD: {redir['original']}")
            click.echo(f"    NEW: {redir['final']}")
    
    if error_count > 0:
        sys.exit(1)


def main():
    """Entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()
