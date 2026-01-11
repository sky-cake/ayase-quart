from .arguments import get_args, Cmd

def main():
    args = get_args()
    match args.cmd_0:
        case Cmd.prep:
            from .prep_cli import prep_cli
            prep_cli(args)
        case Cmd.search:
            import asyncio
            from .search_cli import search_cli
            try:
                asyncio.run(search_cli(args))
            except KeyboardInterrupt:
                pass
        case Cmd.mod:
            pass
