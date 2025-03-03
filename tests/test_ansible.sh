#!/bin/bash -eux
if [ -z "${1-}" ]; then
    echo Pass a playbook path, ie. tests/test_ansible_restful.yml
    exit 1
fi

mkdir -p ~/.ansible/collections/ansible_collections/yourlabs
ln -sfn $PWD/tests/yourlabs/test ~/.ansible/collections/ansible_collections/yourlabs/test
ansible-playbook -i localhost, -c local $@
