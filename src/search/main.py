import asyncio
import sys

from .loader import main as load

help_text = """
usage: python -m search COMMAND [args]
commands:
	load board1 [board2 [board3 ...]]
"""
def print_help():
	print(help_text)

def main(args):
	if not args:
		print_help()
		sys.exit()
	match args[0]:
		case 'load':
			asyncio.run(load(args[1:]))
		case _:
			print_help()
			sys.exit()

if __name__ == "__main__":
	main(sys.argv[1:])