from distutils.command.config import config
import requests, json, csv, io
from config import Config


def verbose_print(x):
    """Attempt to print JSON without altering it, serializable objects as JSON, and anything else as default."""
    if conf.verbose and len(x) > 0:
        if isinstance(x, str):
            print(x)
        else:
            try:
                print(json.dumps(x, indent=4))
            except:
                print(x)


def op_auth(url, email, password):
    # Authenticate and get a JWT
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    auth_data = {"email": email, "password": password}

    r = requests.post(f"{url}/auth/login", json=auth_data, headers=headers)
    r.raise_for_status()
    jwt = r.json()["data"]["token"]

    return jwt


def cc_get_report(report_url):
    """Get data from Campus Cafe's Reporting Services and return list of dicts."""
    auth = (conf.cc.username, conf.cc.password)
    r = requests.get(url=report_url, auth=auth)
    r.raise_for_status()

    r.encoding = "utf-8-sig"
    reader = csv.DictReader(io.StringIO(r.text))
    data = list(reader)

    return data


def op_transform_userlist(list):
    """Transform a list of Openpath users into a dict with email as key."""
    results = {m["identity"]["email"].lower(): m for m in list}

    return results


def op_get_users(group):
    """Get list of users from Openpath with optional group filter."""
    params = {"preFilter": f"group.name:(={group})"}

    url = f"{conf.op.url}/orgs/{conf.op.org_id}/users"
    headers = {"Authorization": f"Bearer {jwt}"}
    r = requests.get(url=url, headers=headers, params=params)
    r.raise_for_status()

    data = r.json()["data"]
    results = op_transform_userlist(data)

    return results


def op_search_user(email, external_id):
    """Get a specific user from Openpath by email and/or external ID."""
    results = {}

    if email:
        params = {"preFilter": f"identity.email:(={email})"}

        url = f"{conf.op.url}/orgs/{conf.op.org_id}/users"
        headers = {"Authorization": f"Bearer {jwt}"}
        r = requests.get(url=url, headers=headers, params=params)
        r.raise_for_status()

        data = r.json()["data"]
        results.update(op_transform_userlist(data))

    if external_id:
        params = {"preFilter": f"externalId:(={external_id})"}

        url = f"{conf.op.url}/orgs/{conf.op.org_id}/users"
        headers = {"Authorization": f"Bearer {jwt}"}
        r = requests.get(url=url, headers=headers, params=params)
        r.raise_for_status()

        data = r.json()["data"]
        results.update(op_transform_userlist(data))

    return results


def op_get_group_id(group):
    pass


def op_add_user_to_group(user, group):
    """Add a user to a group in Openpath."""
    groups = [g["id"] for g in user["groups"]]
    new_group = op_get_group_id(group)
    groups.extend([new_group])

    userid = user["identity"]["id"]
    url = f"{conf.op.url}/orgs/{conf.op.org_id}/users/{userid}/groupIds"
    headers = {"Authorization": f"Bearer {jwt}"}
    r = requests.put(url=url, headers=headers, json=groups)
    r.raise_for_status()

with open("settings.json") as config_file:
    config_json = json.load(config_file)
    conf = Config(config_json)

jwt = op_auth(conf.op.url, conf.op.email, conf.op.password)

for k, v in conf.groups.items():
    verbose_print(f"Synchronizing group {k}")

    # Get list of members from Campus Cafe
    verbose_print(f"Getting report from: {v['source']}...")
    cc_membership = cc_get_report(v["source"])
    cc_membership = {m["USERNAME"].lower(): m for m in cc_membership}
    verbose_print("Campus Cafe membership: " + str(len(cc_membership)))
    # verbose_print(cc_membership)

    # Get list of members from Openpath that correspond to this group
    verbose_print("Getting members from Openpath...")
    op_membership = op_get_users(k)
    verbose_print("Openpath membership: " + str(len(op_membership)))
    # verbose_print(op_membership)

    # Compare lists
    missing = set(cc_membership).difference(set(op_membership))
    verbose_print("Missing from Openpath: " + str(len(missing)))
    # verbose_print(missing)

    extra = set(op_membership).difference(set(cc_membership))
    verbose_print("Extra in Openpath: " + str(len(extra)))
    # verbose_print(extra)

    # Look up missing users in Openpath
    verbose_print("Looking up missing users in Openpath...")
    found = {}

    for m in missing:
        id_number = cc_membership[m]["ID_NUMBER"]
        op_user = op_search_user(m, id_number)
        verbose_print(f"Looking up {m} ({id_number})...found {len(op_user)} matches.")
        found.update(op_user)

    # Add users already in Openpath to group
    verbose_print("Adding existing users to Openpath group...")
    for m in found:
        pass

    # Create new users in Openpath
    verbose_print("Creating new users in Openpath...")
    for m in missing:
        pass
