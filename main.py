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
    # Authenticate and get a JSON Web Token
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
    """Get list of active users from Openpath with optional group filter."""
    params = {"preFilter": f"group.name:(={group}) status:(=A)"}

    url = f"{conf.op.url}/orgs/{conf.op.org_id}/users"
    headers = {"Authorization": f"Bearer {jwt}"}
    r = requests.get(url=url, headers=headers, params=params)
    r.raise_for_status()

    data = r.json()["data"]
    results = op_transform_userlist(data)

    return results


def op_search_user(email=None, external_id=None):
    """Get a specific user from Openpath by email and/or external ID."""
    results = []

    if not email and not external_id:
        raise AttributeError("Must specify either email or external_id.")

    if email:
        params = {"preFilter": f"identity.email:(={email})"}

        url = f"{conf.op.url}/orgs/{conf.op.org_id}/users"
        headers = {"Authorization": f"Bearer {jwt}"}
        r = requests.get(url=url, headers=headers, params=params)
        r.raise_for_status()

        data = r.json()["data"]
        results.extend(data)

    if external_id:
        params = {"preFilter": f"externalId:(={external_id})"}

        url = f"{conf.op.url}/orgs/{conf.op.org_id}/users"
        headers = {"Authorization": f"Bearer {jwt}"}
        r = requests.get(url=url, headers=headers, params=params)
        r.raise_for_status()

        data = r.json()["data"]

        # Make sure we didn't get a duplicate
        if len(data) > 0:
            if data[0]["id"] != results[0]["id"]:
                results.extend(data)

    return results


# def op_get_group_id(group):
#     """Get a group ID from Openpath by name."""
#     params = {"preFilter": f"name:(={group})"}

#     url = f"{conf.op.url}/orgs/{conf.op.org_id}/groups"
#     headers = {"Authorization": f"Bearer {jwt}"}
#     r = requests.get(url=url, headers=headers, params=params)
#     r.raise_for_status()

#     data = r.json()["data"]
#     if len(data) > 1:
#         raise Exception(f"Multiple groups found for {group}")
#     else:
#         group_id = data[0]["id"]

#     return group_id


def op_add_user_to_group(user, group_id):
    """Add a user to a group in Openpath. Expects full User object."""

    payload = {"add": [group_id]}
    userid = user["id"]

    url = f"{conf.op.url}/orgs/{conf.op.org_id}/users/{userid}/groupIds"
    headers = {"Authorization": f"Bearer {jwt}"}
    r = requests.patch(url=url, headers=headers, json=payload)
    r.raise_for_status()


def op_remove_user_from_group(user, group_id):
    """Remove a user from a group in Openpath. Expects full User object."""

    payload = {"remove": [group_id]}
    userid = user["id"]

    url = f"{conf.op.url}/orgs/{conf.op.org_id}/users/{userid}/groupIds"
    headers = {"Authorization": f"Bearer {jwt}"}
    r = requests.patch(url=url, headers=headers, json=payload)
    r.raise_for_status()


def op_create_user(email, first, last, external_id=None, group_id=None):
    """Create a user in Openpath and optionally add to group. Return new user ID."""

    payload = {
        "identity": {
            "email": email,
            "firstName": first,
            "lastName": last,
        },
    }

    if external_id:
        payload["externalId"] = external_id

    url = f"{conf.op.url}/orgs/{conf.op.org_id}/users"
    headers = {"Authorization": f"Bearer {jwt}"}
    r = requests.post(url=url, headers=headers, json=payload)
    r.raise_for_status()

    new_user = r.json()["data"]
    new_userid = new_user["id"]
    if group_id:
        op_add_user_to_group(new_user, group_id)

    return new_userid


def op_update_user(user, email=None, first=None, last=None, external_id=None):
    """Update a user in Openpath. Expects full User object."""

    userid = user["id"]
    payload = {}

    if email:
        payload["identity"] = {"email": email}

    if first:
        payload["identity"] = {"firstName": first}

    if last:
        payload["identity"] = {"lastName": last}

    if external_id:
        payload["externalId"] = external_id

    # Make sure there's something to update
    if len(payload) == 0:
        raise AttributeError("Must specify at least one attribute to update.")

    url = f"{conf.op.url}/orgs/{conf.op.org_id}/users/{userid}"
    headers = {"Authorization": f"Bearer {jwt}"}
    r = requests.patch(url=url, headers=headers, json=payload)
    r.raise_for_status()


def op_set_user_status(user, status):
    """Set user status in Openpath. Expects full User object."""

    if status not in ("A", "I", "S"):
        raise AttributeError(
            "Status must be A (active), I (deleted), or S (suspended)."
        )

    userid = user["id"]
    payload = {"status": status}

    url = f"{conf.op.url}/orgs/{conf.op.org_id}/users/{userid}/status"
    headers = {"Authorization": f"Bearer {jwt}"}
    r = requests.put(url=url, headers=headers, json=payload)
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

    # Get list of Campus Cafe members with holds
    holds_enabled = False
    if "holds" in v and v["holds"] is not None:
        holds_enabled = True
        cc_holds = cc_get_report(v["holds"])
        cc_holds = {m["USERNAME"].lower(): m for m in cc_holds}

    # Get list of members from Openpath that correspond to this group
    verbose_print("Getting members from Openpath...")
    op_membership = op_get_users(k)
    verbose_print("Openpath membership: " + str(len(op_membership)))

    # Compare lists; exlude members with holds
    missing = set(cc_membership).difference(set(op_membership))
    if holds_enabled:
        missing = missing.difference(set(cc_holds))
    verbose_print("Missing from Openpath group: " + str(len(missing)))

    extra = set(op_membership).difference(set(cc_membership))
    verbose_print("Extra in Openpath group: " + str(len(extra)))

    # Look up missing users in Openpath
    found = {}
    verbose_print("Looking up missing users in Openpath...")
    for m in missing:
        id_number = cc_membership[m]["ID_NUMBER"]
        op_user = op_search_user(m, id_number)
        verbose_print(f"Looking up {m} ({id_number})...found {len(op_user)} matches.")
        if len(op_user) > 1:
            raise Exception(f"Multiple Openpath users found for {m} ({id_number})")
        elif len(op_user) == 1:
            found.update({m: op_user[0]})

    # Add found users to group, update status, or update email address in Openpath
    for m in found:
        if str(m).lower() != found[m]["identity"]["email"].lower():
            verbose_print(f"Updating email address for {m}")
            op_update_user(found[m], email=cc_membership[m]["USERNAME"])
        elif len([g for g in found[m]["groups"] if g["id"] == v["id"]]) == 0:
            verbose_print(f"Adding {m} to group {k}")
            op_add_user_to_group(found[m], v["id"])
        elif m["Status"] != "A":
            verbose_print(f"Updating status for {m} to Active")
            op_set_user_status(found[m], "A")
        else:
            verbose_print(f"Unsure what to do with {m}. Skipping user.")

        missing.remove(m)

    # Create new users in Openpath group
    for m in missing:
        verbose_print("Creating new users in Openpath...")
        id_number = cc_membership[m]["ID_NUMBER"]
        first = cc_membership[m]["FIRST_NAME"]
        last = cc_membership[m]["LAST_NAME"]
        new_userid = op_create_user(m, first, last, id_number, k)
        # Todo: upload user's picture
        verbose_print(
            f"New user {m} created with Openpath ID {new_userid} and added to {k}."
        )

    # Remove extra users from Openpath group
    for m in extra:
        verbose_print(f"Removing {m} from group {k}")
        op_remove_user_from_group(op_membership[m], v["id"])

    # Find users in Openpath missing external_id and update
    verbose_print("Refreshing Openpath membership...")
    op_membership = op_get_users(k)
    missing_external_id = [
        kk
        for kk, vv in op_membership.items()
        if vv["externalId"] is None and kk in cc_membership and vv["status"] == "A"
    ]
    if len(missing_external_id) > 0:
        verbose_print(
            f"Updating {str(len(missing_external_id))} Openpath users missing external_id..."
        )

    for m in missing_external_id:
        verbose_print(f"Updating external_id for {m}")
        external_id = cc_membership[m]["ID_NUMBER"]
        op_update_user(op_membership[m], external_id=external_id)

    # Suspend users in Openpath present in Campus Cafe holds list
    if holds_enabled:
        verbose_print(
            f"{len(cc_holds)} users on hold...checking that all are suspended in Openpath..."
        )
        for m in cc_holds:
            if m in op_membership:
                verbose_print(f"Suspending {m}")
                op_set_user_status(op_membership[m], "S")

# Todo: Delete any Openpath users not in any groups (to preserve license seats)

verbose_print("Done!")
