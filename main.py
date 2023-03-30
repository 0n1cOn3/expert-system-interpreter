import sys
from ess.shell import Shell

if __name__ == '__main__':

    shell = Shell()

    if len(sys.argv) > 1:
        if len(sys.argv) > 2:
            print("Bad argument, usage is: main.py FILEPATH")
            sys.exit(-1)

        shell.load_from_file(sys.argv[1])
    try:
        shell.start()
    except KeyboardInterrupt:
        sys.exit(0)
