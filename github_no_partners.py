# github_no_partners.py
# Dan Wallach <dwallach@rice.edu>
# Available subject to the Apache 2.0 License
# https://www.apache.org/licenses/LICENSE-2.0

import argparse
import pandas as pd
from github_config import *
from github_scanner import *

# your graders, preferably their GitHub IDs (we'll ignore them if they've also checked out a copy of the assignment)
grader_list = default_grader_list

# your own GitHub ID and/or anybody else who you wish to exclude from being graded
ignore_list = default_grader_ignore_list

# command-line argument processing

parser = argparse.ArgumentParser(description='find all students with no partners and/or no repo')
parser.add_argument('--token',
                    nargs=1,
                    default=[default_github_token],
                    help='GitHub API token')
parser.add_argument('--org',
                    nargs=1,
                    default=[default_github_organization],
                    help='GitHub organization to scan, default: ' + default_github_organization)
parser.add_argument('--prefix',
                    nargs=1,
                    default=[default_prefix],
                    help='Prefix on projects to match (default: match all projects)')
parser.add_argument('--students',
                    nargs=1,
                    default=[default_student_csv_name],
                    help="CSV file name with student information (default: student-info.csv)")
parser.add_argument('--ignore',
                    nargs=1,
                    default=[""],
                    help="string pattern in group names to ignore, e.g., STAFF (no default)")
parser.add_argument('--min_team_size',
                    nargs=1,
                    default=["2"],
                    help="minimum team size (default: 2)")

args = parser.parse_args()

github_prefix = args.prefix[0]
github_organization = args.org[0]
github_token = args.token[0]
student_file_name = args.students[0]
ignore_str = args.ignore[0]
min_team_size = int(args.min_team_size[0])

df_students = {}  # will replace below
df_students_success = False
try:
    df_students = pd.read_csv(student_file_name)
    # force lower-case of GitHub IDs
    df_students.GitHubID = df_students.GitHubID.astype(str).str.lower()  # force lower-case of GitHub IDs
    df_students_success = True
except FileNotFoundError:
    print("Cannot file student info file: %s\n" % student_file_name)
    pass


def student_known(github_id: str) -> bool:
    """
    Given a GitHub IDs, returns whether that student is a known student in
    the student-data CSV file.
    """
    if df_students_success:
        matches = df_students[df_students['GitHubID'] == github_id.lower()]
        if len(matches) == 1:
            return True
        elif len(matches) == 0:
            return False
        else:
            print("Warning: two or more rows found for github-id (%s) in s info!\n" % github_id)
            return True
    else:
        return False


def student_info(github_id: str) -> str:
    """
    Given a GitHub IDs, returns a suitably human-readable string based on
    the student-data CSV file with the students' name, email, etc.
    """
    if df_students_success:
        matches = df_students[df_students['GitHubID'] == github_id.lower()]
        if len(matches) == 1:
            s = matches.iloc[0].to_dict()
        elif len(matches) == 0:
            print("Warning: github-id (%s) not found in s info!\n" % github_id)
            s = {'NetID': '', 'Name': '', 'Email': '', 'GitHubID': github_id}
        else:
            print("Warning: two or more rows found for github-id (%s) in s info!\n" % github_id)
            s = matches.iloc[0].to_dict()
        if 'NetID' in s and s['Email'].startswith(s['NetID']):
            return "%s <%s>" % (s['Name'], s['Email'])
        else:
            return "%s <%s> (%s)" % (s['Name'], s['Email'], s['NetID'])
    else:
        return github_id


ids_seen = {}
submissions = {}
all_ignore_list = ignore_list + grader_list

filtered_repo_list = [x for x in query_matching_repos(github_organization, github_prefix, github_token)
                      if desired_user(github_prefix, all_ignore_list, x['name'], ignore_str)]

team_info = fetch_team_infos(filtered_repo_list, github_token, True)

gid_to_repo = {}
duplicates = {}
num_students_in_repos_below_size = 0
num_students_in_no_repo = 0

print("=========================================")

for repo in filtered_repo_list:
    if 'html_url' in repo:
        repo['final_url'] = repo['html_url']
    else:
        repo['final_url'] = repo['url']

    gids = team_info[repo['final_url']]['team_members']

    if len(gids) < min_team_size:
        for gid in gids:
            print("%s in a repo below min size (%d)" % (student_info(gid), min_team_size))
            print("  - %s" % repo['final_url'])
            num_students_in_repos_below_size = num_students_in_repos_below_size  + 1

    for gid in gids:
        gid_lower = gid.lower()
        if gid_lower in gid_to_repo:
            if gid_lower in duplicates:
                duplicates[gid_lower][repo['final_url']] = True
            else:
                duplicates[gid_lower] = {}
                duplicates[gid_lower][repo['final_url']] = True
                duplicates[gid_lower][gid_to_repo[gid_lower]] = True
        gid_to_repo[gid_lower] = repo['final_url']

if not df_students_success:
    print("No student database: cannot determine if we have missing students")
else:
    for student in df_students['GitHubID']:
        if student not in gid_to_repo:
            print("%s not attached to any repos" % student_info(student))
            num_students_in_no_repo = num_students_in_no_repo + 1

    for gid in gid_to_repo.keys():
        if not student_known(gid):
            print("Unknown user <%s> is attached to a repo but isn't in the student database" % gid)
            print("  - %s" % gid_to_repo[gid])

for student in duplicates.keys():
    print("%s appears in more than one repo!" % student_info(student))
    for repo in duplicates[student].keys():
        print("  - %s" % repo)

print("=========================================")

if df_students_success:
    print("Students with repos / students in database: %d / %d" % (len(gid_to_repo), len(df_students['GitHubID'])))
    print("Students in repos with below the minimum number of partners: %d" % num_students_in_repos_below_size)
    print("Students in no repo at all: %d" % num_students_in_no_repo)
