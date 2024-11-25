import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import os

log_links_dict = {}

def fetch_log_links(url, base_url=None, allow=True):
    if base_url is None:
        base_url = url

    if url not in log_links_dict:
        log_links_dict[url] = []

    try:
        response = requests.get(url)
        response.raise_for_status()
        page_content = response.text

        soup = BeautifulSoup(page_content, 'html.parser')

        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            absolute_url = urljoin(url, href)

            if href.endswith('.log'):
                if not any(log["opt_in"] == absolute_url for log in log_links_dict[url]):
                    log_links_dict[url].append({
                        "opt_in": absolute_url
                    })

            elif href.endswith('/') and allow:
                fetch_log_links(absolute_url, base_url, False)

    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")

def process_log_file(file_url,pc=set()):
    response = requests.get(file_url)
    file_path = 'temp_file.log'

    try:
        response.raise_for_status()
        with open(file_path, 'wb') as file:
            file.write(response.content)

        result = []
        ceph_version = None

        with open(file_path, 'r') as file:
            lines = file.readlines()
            print("=" * 50)
            print(file_url)
            print("=" * 50)

            for i in range(len(lines)):
                # if 'Execute cephadm shell -- radosgw-admin' in lines[i]:
                    # print("Hiiii",version_line.split())
                    
                      
                    # if ceph_version :
                    #     # ceph_version = version
                    #     print(f"ceph_version: {ceph_version}")
                    

                if 'Execute cephadm shell -- radosgw-admin' in lines[i]:
                    version_line = lines[i + 2].strip()
                    # version = " ".join(version_line.split()[:2])
                    ceph_version=".".join(version_line.split()[5].split(".")[6:9])
                    index = lines[i].find('radosgw-admin')
                    command = lines[i][index:].rstrip("\n")
                    if command in pc:
                        continue
                    stack = []
                    json_start = None
                    json_content = ""

                    for j in range(i + 1, len(lines)):
                        for char in lines[j]:
                            if char == '{':
                                if not stack:
                                    json_start = j
                                stack.append('{')
                            if stack:
                                json_content += char
                            if char == '}':
                                stack.pop()
                                if not stack:
                                    break
                        if not stack and json_content:
                            break

                    if json_content:
                        cleaned_output_line = (
                            json_content.replace("'", "\"")
                            .replace("True", "true")
                            .replace("False", "false")
                            .strip()
                        )

                        try:
                            json_output = json.loads(cleaned_output_line)
                        except json.JSONDecodeError:
                            json_output = None

                        if json_output:
                            result.append({
                                "command": command,
                                "output": json_output
                            })
                            pc.add(command)

        json_data = {
            "ceph_versions": [f"{ceph_version}"] if ceph_version else [],
            "radosgw_outputs": result
        }

        os.remove(file_path)

        return json_data

    except requests.RequestException as e:
        print(f"Failed to download file at url {file_url}: {e}")
        return {}

def process_all_log_files(url):
    fetch_log_links(url)
    pc=set()
    for directories in log_links_dict:
        log_files_dict_list = log_links_dict[directories]

        for log_files_dict in log_files_dict_list:
            processing_result = process_log_file(log_files_dict["opt_in"],pc)
            log_files_dict["scan_result"] = processing_result

    with open("alloutput.json", 'w') as file:
        json.dump(log_links_dict, file, indent=4)

url = "http://magna002.ceph.redhat.com/cephci-jenkins/results/openstack/RH/8.0/rhel-9/Regression/19.2.0-12/rgw/36/"
process_all_log_files(url)