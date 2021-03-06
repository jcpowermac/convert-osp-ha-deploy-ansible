
import sys
import re
import yaml
from subprocess import Popen, PIPE

file = None

def execute_process(cmd_line):
    print cmd_line
    try:
        process = Popen(cmd_line, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
        output, err = process.communicate()
        return_code = process.returncode
        return output, err, return_code
    except Exception as e:
        print str(e)
        sys.exit(1)


def split_openstack_config_arguments(line):
    args = line.split()
    args.insert(1, "--verbose")

    count = 0
    for a in args:
        if a.find("${") != -1:
            args[count] = a.replace("${", "{{ ")
            args[count] = args[count].replace("}", " }}")
        count += 1

    space = " "
    new_line = space.join(args)

    output = """\n- name: openstack-command set %s
  command: %s
  register: cmd
  changed_when: \"'changed' in cmd.stderr\"\n""" % (args[5], new_line)
    #print output
    file.writelines(output)


def split_yum_arguments(line):
    args = line.split()
    new_args = []
    space = " "

    for a in args:
        if "yum" in a:
            continue
        elif "-y" in a:
            continue
        elif "install" in a:
            continue
        else:
            new_args.append(a)

    with_items = yaml.dump(new_args, default_flow_style=False)
    output = """\n- name: Install software
  yum: name={{ item }} state=present
  with_items:\n%s\n""" % with_items
    file.writelines(output)

def match_yum_line(line):
    match = re.search("^yum", line)
    if match is not None:
        split_yum_arguments(line)
        return True
    return False

def match_openstack_config_line(line):
    match = re.search("^openstack-config", line)
    if match is not None:
        split_openstack_config_arguments(line)
        return True
    return False

def split_systemctl_arguments(line):
    args = line.split()
    parameters = "- name: %s" % line
    write_to_file = False

    for a in args:
        if "enable" in a:
            parameters += "  service: name=%s enabled=yes state=started\n" % args[1]
            write_to_file = True
        elif "disable" in a:
            parameters += "  service: name=%s enabled=no state=stopped\n" % args[1]
            write_to_file = True
    if write_to_file:
        file.writelines(parameters)

def match_systemctl_line(line):
    match = re.search("^systemctl", line)
    if match is not None:
        split_systemctl_arguments(line)
        return True
    return False

def main():
    global file
    filename = sys.argv[1]
    f = open(filename, 'r')
    service = filename.split(".")

    output, err, return_code = execute_process("/usr/bin/ansible-galaxy init %s" % service[0])

    file = open("%s/tasks/main.yml" % service[0], "w+")
    file.writelines("---\n")

    for line in f:
        result = match_openstack_config_line(line)
        if not result:
            result = match_yum_line(line)
        if not result:
            match_systemctl_line(line)

    file.close()
if __name__ == '__main__':
    main()