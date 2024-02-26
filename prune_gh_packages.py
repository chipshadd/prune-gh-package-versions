import requests
import urllib.parse
from configparser import ConfigParser
from datetime import datetime, timedelta
import re

def get_packages():
    final = {}
    for type in TYPES:
        final.update(get_packages_of_type(type))
    return final

def get_packages_of_type(type):
    print(type)
    response = {}
    def parse(json):
        for package in json:
            repo_name = package["repository"]["name"]
            package_name = package["name"]
            if re.match(MATCH_PACKAGE, package_name) and re.match(MATCH_REPO, repo_name):
                # starting to feel jenky here...
                if repo_name not in response:
                    response[repo_name] = {}
                if type not in response[repo_name]:
                    response[repo_name][type] = {}
                response[repo_name][type][package_name] = get_versions(type, package_name)
                print(f'{repo_name=}, {type=}, {package_name=}')

    next_url = f'{URL}?package_type={type}&per_page=100'
    while (next_url is not None):
        packages = requests.get(next_url, headers=HEADERS)
        print(f'(Rate limit: {packages.headers["X-RateLimit-Used"]}/{packages.headers["X-RateLimit-Limit"]})')
        parse(packages.json())
        next_url = get_pagination(packages.headers)
    return response

def get_versions(type, name):
    final = {"tagged": [], "untagged": []}
    def parse(json):
        for package in json:
            age = CURRENT_DATE - datetime.strptime(package['updated_at'], "%Y-%m-%dT%H:%M:%SZ")
            package["age"] = age.days
            data = {'id': package['id'], 'url': package['html_url'], 'age': age.days}
            if len(package["metadata"]["container"]["tags"]) == 0 and DELETE_UNTAGGED != 'none':
                if DELETE_UNTAGGED == 'all' or DELETE_UNTAGGED == 'only':
                    stats["untagged"] += 1
                    final["untagged"].append(data)
                    continue
                if age.days > LAST_UPDATED:
                    final["untagged"].append(data)
                    stats["untagged"] += 1
                    continue
            else:
                if re.match(MATCH_TAG, ''.join(package["metadata"]["container"]["tags"])):
                    if age.days > LAST_UPDATED:
                        data["tags"] =  package["metadata"]["container"]["tags"]
                        stats["tagged"] += 1
                        final["tagged"].append(data)
        print(f'Found: tagged: {len(final["tagged"])}, untagged: {len(final["untagged"])}')
    safe_name = urllib.parse.quote(name, safe='')
    next_url = f'{URL}/{type}/{safe_name}/versions?per_page=100'
    while (next_url is not None):
        package = requests.get(next_url, headers=HEADERS)
        print(f'(Rate limit: {package.headers["X-RateLimit-Used"]}/{package.headers["X-RateLimit-Limit"]})')
        parse(package.json())
        next_url = get_pagination(package.headers)
    print()
    return final

def delete_version(type, repo, name, id):
    safe_name = urllib.parse.quote(name, safe='')
    packages = requests.delete(f'{URL}/{type}/{safe_name}/versions/{id}', headers=HEADERS)
    if packages.status_code == 204:
        print(f'{repo}/{name}/{id} has been deleted', end='')
    if packages.status_code == 401:
        print("Token is not authenticated", end='')
    if packages.status_code == 403:
        print(f'Token is not authorized to delete {repo}/{name}/{id}', end='')
    if packages.status_code == 404:
        print(f'{repo}/{name}/{id} was not found.', end='')
    print(f'(Rate limit: {packages.headers["X-RateLimit-Used"]}/{packages.headers["X-RateLimit-Limit"]})')

def get_pagination(headers):
    # Pagination is in the following format as a string at the 'Link' key:
    # '<https://api.github.com/organizations/<org_id>/packages?package_type=container&per_page=1&page=2>; rel="next", <https://api.github.com/organizations/<org_id>/packages?package_type=container&per_page=1&page=23>; rel="last"'
    if 'Link' in headers:
            if 'rel="next"' in headers['Link']:
                remove_chars = set('<>;')
                return ''.join(c for c in headers['Link'].split()[0] if c not in remove_chars)
    return None

def main():
    packages = get_packages()
    # for package in get_packages('container'):
    print("The following packages will be deleted:")
    for repo, types in packages.items():
        for type, versions in types.items():
            for package, tags in versions.items():
                for x in tags["untagged"]:
                    print(f'{x["id"]} - {x["age"]} days old - {x["url"]}')
                for x in tags["tagged"]:
                    print(f'{x["tags"]} - {x["age"]} days old - {x["url"]}')
    confirm = 'no'
    print(f'{stats["tagged"]} tagged, {stats["untagged"]} untagged.')
    if SKIP == 'false':
        print("Type in 'yes' at the prompt delete all of the above packages:  ")
        confirm = input('     prompt: ')
    else:
        confirm = 'yes'
    if confirm == 'yes':
        print()
        print("Deleting packages.")
        for repo, types in packages.items():
            for type, versions in types.items():
                for package, tags in versions.items():
                    for tagged in tags['tagged']:
                        delete_version(type, repo, package, tagged["id"])
                    for untagged in tags['untagged']:
                        delete_version(type, repo, package, untagged["id"])

            
if __name__ == "__main__":
    config = ConfigParser()
    config.read('config.ini')
    stats = { "untagged": 0, "tagged": 0}
    # Assign constants
    GH_URL = config['gh']['url'].rstrip('/')
    AUTH = config['gh']['token']
    ORG = config['gh']['org_name']
    LAST_UPDATED = int(config['package']['last_updated'])
    DELETE_UNTAGGED = config['global']['delete_untagged'].lower()
    assert DELETE_UNTAGGED in ['all', 'normal', 'only'], "global.delete_untagged in config.ini needs to be one of: ['all', 'only, 'normal']"
    TYPES = config['package']['types'].split(',')
    for type in TYPES:
        assert type.strip() in ['all', 'npm','maven','rubygems','docker','nuget','container' ], f"'{type}' is not a valid package type."
    SKIP = config['global']['unattended'].lower()
    assert SKIP in ['true', 'false'], "global.unattended needs to be one of: ['true', 'false']"
    MATCH_PACKAGE = config['filters']['package_name_match_pattern']
    MATCH_REPO = config['filters']['repository_name_match_pattern']
    MATCH_TAG = config['filters']['package_tag_match_pattern']
    CURRENT_DATE = datetime.utcnow()
    URL = f'{GH_URL}/orgs/{ORG}/packages'
    HEADERS = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": f'Bearer {AUTH}'
    }
    main()