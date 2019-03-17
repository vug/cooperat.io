import argparse
from multiprocessing.dummy import Pool as ThreadPool
from subprocess import Popen, PIPE


def parse_arguments():
    parser = argparse.ArgumentParser(description="Create multiple bots for testing.")
    parser.add_argument(
        "--num-warriors", "-w", help="Number of warrior bots.", type=int, required=True
    )
    parser.add_argument(
        "--num-psychics", "-p", help="Number of warrior bots.", type=int, required=True
    )
    args = parser.parse_args()
    return args


def function_create_cmds(cmd):
    proc = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    (output, error) = proc.communicate()
    return output


if __name__ == "__main__":
    args = parse_arguments()
    num_warriors = args.num_warriors
    num_psychics = args.num_psychics

    num_bots = num_warriors + num_psychics
    cmds = [
        f"python test_client.py --unit-class warrior --nickname warrior-{k}"
        for k in range(num_warriors)
    ]
    cmds.extend(
        [
            f"python test_client.py --unit-class psychic --nickname psychic-{k}"
            for k in range(num_psychics)
        ]
    )

    pool = ThreadPool(num_bots)
    results = pool.map(function_create_cmds, cmds)
    pool.close()
    pool.join()
    print(results)
