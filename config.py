import json


class Config:
    def __init__(self, config):
        self.op = self.Openpath(config["Openpath"])
        self.cc = self.CampusCafe(config["CampusCafe"])
        self.groups = config["groups"]
        self.verbose = config["verbose"]

    class Openpath:
        def __init__(self, config):
            self.url = config["url"]
            self.org_id = config["org_id"]
            self.email = config["email"]
            self.password = config["password"]

    class CampusCafe:
        def __init__(self, config):
            self.username = config["username"]
            self.password = config["password"]
            self.url = config["url"]
