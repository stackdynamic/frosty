import json
from os import path


def gen_config():
    config = {}
    for param in PARAMS:
        value = input("{}: ".format(param)).strip()
        if value.isdigit():
            value = int(value)
        config[param] = value
    with open("config.json", "w") as f:
        f.write(json.dumps(config))
    return config


def get_config():
    if path.exists("config.json"):
        with open("config.json") as f:
            config = json.load(f)
            if PARAMS != set(config.keys()):
                print("Invalid configuration file. Generating new file.")
                return gen_config()
            else:
                return config

    else:
        print("No configuration file for Frosty found. Generating new file.")
        return gen_config()


PARAMS = {"bot_token"}
PROFILE = get_config()
