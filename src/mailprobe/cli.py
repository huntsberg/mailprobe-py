"""
Command-line interface for MailProbe-Py.

This module provides the main CLI entry point and command implementations
that match the original MailProbe functionality.
"""

import sys
import click
from pathlib import Path
from typing import List, Optional, TextIO

from .config import ConfigManager, MailProbeConfig, get_default_config_path
from .filter import MailFilter
from .message import EmailMessageReader, EmailMessage


# Global configuration object
_config: Optional[MailProbeConfig] = None
_config_manager: Optional[ConfigManager] = None


def get_config() -> MailProbeConfig:
    """Get the global configuration object."""
    global _config
    if _config is None:
        _config = MailProbeConfig()
    return _config


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


@click.group(invoke_without_command=True)
@click.option(
    "-d", "--database-path", type=click.Path(), help="Database directory path"
)
@click.option(
    "-c",
    "--create-db-dir",
    is_flag=True,
    help="Create database directory if it does not exist",
)
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output")
@click.option("--debug", is_flag=True, help="Enable debug output")
@click.option(
    "-f", "--config-file", type=click.Path(exists=True), help="Configuration file path"
)
@click.option(
    "-l", "--spam-threshold", type=float, help="Spam probability threshold (0.0-1.0)"
)
@click.option(
    "-C",
    "--min-word-count",
    type=int,
    help="Minimum word count for calculated probability",
)
@click.option(
    "-p", "--max-phrase-terms", type=int, help="Maximum number of words per phrase"
)
@click.option(
    "-w", "--terms-for-score", type=int, help="Number of terms to use for scoring"
)
@click.option(
    "-r", "--max-word-repeats", type=int, help="Maximum repeats of same word in scoring"
)
@click.option("-s", "--cache-size", type=int, help="Database cache size")
@click.option("-h", "--no-remove-html", is_flag=True, help="Do not remove HTML tags")
@click.option("-x", "--extend-top-terms", is_flag=True, help="Extend top terms array")
@click.option(
    "-X", "--aggressive-scoring", is_flag=True, help="Use aggressive scoring settings"
)
@click.option(
    "-o", "--option", multiple=True, help="Special options (graham, conservative, etc.)"
)
@click.pass_context
def cli(ctx, **kwargs):
    """MailProbe-Py: Bayesian email classifier."""
    global _config, _config_manager

    # Initialize configuration manager
    config_file = kwargs.get("config_file")
    if config_file:
        _config_manager = ConfigManager(Path(config_file))
    else:
        _config_manager = ConfigManager()

    # Load configuration
    _config = _config_manager.load_config()

    # Update from command line arguments
    args = {k: v for k, v in kwargs.items() if v is not None}
    _config_manager.update_from_args(args)

    # Apply special options
    for option in kwargs.get("option", []):
        if option in ["graham", "conservative", "aggressive", "fast"]:
            _config_manager.apply_preset(option)

    # Handle aggressive scoring shortcut
    if kwargs.get("aggressive_scoring"):
        _config.scoring.terms_for_score = 5
        _config.scoring.max_word_repeats = 5
        _config.scoring.extend_top_terms = True

    # Store config in context
    ctx.ensure_object(dict)
    ctx.obj["config"] = _config

    # If no command specified, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.pass_context
def create_db(ctx):
    """Create a new spam database."""
    config = ctx.obj["config"]
    db_path = config.get_database_path()

    if config.verbose:
        click.echo(f"Creating database in {db_path}")

    # Initialize filter (this creates the database)
    with MailFilter(db_path, config.to_filter_config()) as spam_filter:
        info = spam_filter.get_database_info()
        click.echo(f"Database created successfully at {info['database_path']}")


@cli.command()
@click.argument("files", nargs=-1, type=click.Path(exists=True))
@click.pass_context
def receive(ctx, files):
    """Score message and update database (always trains)."""
    config = ctx.obj["config"]

    with MailFilter(
        config.get_database_path(), config.to_filter_config()
    ) as spam_filter:
        reader = EmailMessageReader()

        if files:
            # Process files
            for file_path in files:
                _process_messages_receive(
                    spam_filter, reader, Path(file_path), config.verbose
                )
        else:
            # Process stdin
            message = reader.read_from_stdin()
            score = spam_filter.score_message(message)

            # Always train in receive mode
            is_spam = score.is_spam
            spam_filter.train_message(message, is_spam, force_update=True)

            # Output result
            result = "SPAM" if is_spam else "GOOD"
            click.echo(f"{result} {score.probability:.7f} {message.digest}")


@cli.command()
@click.argument("files", nargs=-1, type=click.Path(exists=True))
@click.pass_context
def train(ctx, files):
    """Score message and selectively update database (train mode)."""
    config = ctx.obj["config"]

    with MailFilter(
        config.get_database_path(), config.to_filter_config()
    ) as spam_filter:
        reader = EmailMessageReader()

        if files:
            # Process files
            for file_path in files:
                _process_messages_train(
                    spam_filter, reader, Path(file_path), config.verbose
                )
        else:
            # Process stdin
            message = reader.read_from_stdin()
            score = spam_filter.score_message(message)

            # Selective training in train mode
            is_spam = score.is_spam
            updated = spam_filter.train_message_selective(message, is_spam)

            if config.verbose and updated:
                click.echo(f"Updated database for message {message.digest[:8]}")

            # Output result
            result = "SPAM" if is_spam else "GOOD"
            click.echo(f"{result} {score.probability:.7f} {message.digest}")


@cli.command()
@click.argument("files", nargs=-1, type=click.Path(exists=True))
@click.option(
    "-T", "--show-terms", is_flag=True, help="Show top terms used for scoring"
)
@click.pass_context
def score(ctx, files, show_terms):
    """Score messages without updating database."""
    config = ctx.obj["config"]

    with MailFilter(
        config.get_database_path(), config.to_filter_config()
    ) as spam_filter:
        reader = EmailMessageReader()

        if files:
            # Process files
            for file_path in files:
                _process_messages_score(
                    spam_filter, reader, Path(file_path), show_terms
                )
        else:
            # Process stdin
            message = reader.read_from_stdin()
            score = spam_filter.score_message(message)

            # Output result
            result = "SPAM" if score.is_spam else "GOOD"
            click.echo(f"{result} {score.probability:.7f} {message.digest}")

            if show_terms:
                _show_top_terms(score)


@cli.command()
@click.argument("files", nargs=-1, type=click.Path(exists=True))
@click.pass_context
def good(ctx, files):
    """Mark messages as non-spam (good)."""
    config = ctx.obj["config"]

    with MailFilter(
        config.get_database_path(), config.to_filter_config()
    ) as spam_filter:
        reader = EmailMessageReader()
        count = 0

        if files:
            for file_path in files:
                count += _process_messages_classify(
                    spam_filter, reader, Path(file_path), False, config.verbose
                )
        else:
            message = reader.read_from_stdin()
            spam_filter.train_message(message, False, force_update=True)
            count = 1

        if config.verbose:
            click.echo(f"Processed {count} messages as good")


@cli.command()
@click.argument("files", nargs=-1, type=click.Path(exists=True))
@click.pass_context
def spam(ctx, files):
    """Mark messages as spam."""
    config = ctx.obj["config"]

    with MailFilter(
        config.get_database_path(), config.to_filter_config()
    ) as spam_filter:
        reader = EmailMessageReader()
        count = 0

        if files:
            for file_path in files:
                count += _process_messages_classify(
                    spam_filter, reader, Path(file_path), True, config.verbose
                )
        else:
            message = reader.read_from_stdin()
            spam_filter.train_message(message, True, force_update=True)
            count = 1

        if config.verbose:
            click.echo(f"Processed {count} messages as spam")


@cli.command()
@click.argument("files", nargs=-1, type=click.Path(exists=True))
@click.pass_context
def remove(ctx, files):
    """Remove messages from database."""
    config = ctx.obj["config"]

    with MailFilter(
        config.get_database_path(), config.to_filter_config()
    ) as spam_filter:
        reader = EmailMessageReader()
        count = 0

        if files:
            for file_path in files:
                for message in reader.read_from_file(file_path):
                    if spam_filter.remove_message(message):
                        count += 1
                        if config.verbose:
                            click.echo(f"Removed message {message.digest[:8]}")
        else:
            message = reader.read_from_stdin()
            if spam_filter.remove_message(message):
                count = 1

        if config.verbose:
            click.echo(f"Removed {count} messages from database")


@cli.command()
@click.option(
    "--max-count", type=int, default=2, help="Maximum count for words to be removed"
)
@click.option(
    "--max-age-days",
    type=int,
    default=7,
    help="Maximum age in days for words to be removed",
)
@click.pass_context
def cleanup(ctx, max_count, max_age_days):
    """Clean up old/rare words from database."""
    config = ctx.obj["config"]

    with MailFilter(
        config.get_database_path(), config.to_filter_config()
    ) as spam_filter:
        removed = spam_filter.cleanup_database(max_count, max_age_days)
        click.echo(f"Removed {removed} words from database")


@cli.command()
@click.option(
    "--max-count", type=int, default=2, help="Maximum count for words to be removed"
)
@click.pass_context
def purge(ctx, max_count):
    """Purge words with low counts regardless of age."""
    config = ctx.obj["config"]

    with MailFilter(
        config.get_database_path(), config.to_filter_config()
    ) as spam_filter:
        removed = spam_filter.purge_database(max_count)
        click.echo(f"Purged {removed} words from database")


@cli.command()
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["csv", "json"]),
    default="csv",
    help="Output format",
)
@click.pass_context
def dump(ctx, output_format):
    """Export database contents."""
    config = ctx.obj["config"]

    with MailFilter(
        config.get_database_path(), config.to_filter_config()
    ) as spam_filter:
        words = spam_filter.export_database()

        if output_format == "csv":
            click.echo("term,good_count,spam_count")
            for term, good_count, spam_count in words:
                click.echo(f'"{term}",{good_count},{spam_count}')
        elif output_format == "json":
            import json

            data = [
                {"term": term, "good_count": good, "spam_count": spam}
                for term, good, spam in words
            ]
            click.echo(json.dumps(data, indent=2))


@cli.command()
@click.argument("import_file", type=click.File("r"))
@click.pass_context
def import_db(ctx, import_file):
    """Import database from CSV file."""
    config = ctx.obj["config"]

    with MailFilter(
        config.get_database_path(), config.to_filter_config()
    ) as spam_filter:
        import csv

        reader = csv.reader(import_file)
        next(reader)  # Skip header

        word_data = []
        for row in reader:
            if len(row) >= 3:
                term = row[0].strip('"')
                good_count = int(row[1])
                spam_count = int(row[2])
                word_data.append((term, good_count, spam_count))

        imported = spam_filter.import_database(word_data)
        click.echo(f"Imported {imported} words into database")


@cli.command()
@click.pass_context
def info(ctx):
    """Show database information."""
    config = ctx.obj["config"]

    with MailFilter(
        config.get_database_path(), config.to_filter_config()
    ) as spam_filter:
        info = spam_filter.get_database_info()

        click.echo("Database Information:")
        click.echo(f"  Path: {info['database_path']}")
        click.echo(f"  Words: {info['word_count']:,}")
        click.echo(f"  Good messages: {info['good_message_count']:,}")
        click.echo(f"  Spam messages: {info['spam_message_count']:,}")
        click.echo(f"  Total messages: {info['total_message_count']:,}")
        click.echo(f"  File size: {info['database_file_size']:,} bytes")
        click.echo(f"  Cache size: {info['cache_size']}")


@cli.command()
@click.pass_context
def create_config(ctx):
    """Create a default configuration file."""
    config = ctx.obj["config"]
    config_path = get_default_config_path()

    get_config_manager().save_config(config, config_path)
    click.echo(f"Configuration file created at {config_path}")


def _process_messages_receive(
    spam_filter: MailFilter, reader: EmailMessageReader, file_path: Path, verbose: bool
) -> int:
    """Process messages in receive mode."""
    count = 0
    for message in reader.read_from_file(file_path):
        score = spam_filter.score_message(message)
        is_spam = score.is_spam
        spam_filter.train_message(message, is_spam, force_update=True)

        if verbose:
            result = "SPAM" if is_spam else "GOOD"
            click.echo(f"{result} {score.probability:.7f} {message.digest}")

        count += 1

    return count


def _process_messages_train(
    spam_filter: MailFilter, reader: EmailMessageReader, file_path: Path, verbose: bool
) -> int:
    """Process messages in train mode."""
    count = 0
    for message in reader.read_from_file(file_path):
        score = spam_filter.score_message(message)
        is_spam = score.is_spam
        updated = spam_filter.train_message_selective(message, is_spam)

        if verbose:
            result = "SPAM" if is_spam else "GOOD"
            status = " (updated)" if updated else ""
            click.echo(f"{result} {score.probability:.7f} {message.digest}{status}")

        count += 1

    return count


def _process_messages_score(
    spam_filter: MailFilter,
    reader: EmailMessageReader,
    file_path: Path,
    show_terms: bool,
) -> int:
    """Process messages in score mode."""
    count = 0
    for message in reader.read_from_file(file_path):
        score = spam_filter.score_message(message)

        result = "SPAM" if score.is_spam else "GOOD"
        click.echo(f"{result} {score.probability:.7f} {message.digest}")

        if show_terms:
            _show_top_terms(score)

        count += 1

    return count


def _process_messages_classify(
    spam_filter: MailFilter,
    reader: EmailMessageReader,
    file_path: Path,
    is_spam: bool,
    verbose: bool,
) -> int:
    """Process messages for classification."""
    count = 0
    for message in reader.read_from_file(file_path):
        spam_filter.train_message(message, is_spam, force_update=True)

        if verbose:
            classification = "spam" if is_spam else "good"
            click.echo(f"Classified {message.digest[:8]} as {classification}")

        count += 1

    return count


def _show_top_terms(score) -> None:
    """Show top terms used for scoring."""
    if score.top_terms:
        click.echo("Top terms:")
        for term, prob, count in score.top_terms:
            click.echo(f"  {term}: {prob:.3f} (count: {count})")


def main():
    """Main entry point for the CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\nInterrupted by user", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
