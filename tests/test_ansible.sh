#!/bin/bash -eux
mkdir -p ~/.ansible/collections/ansible_collections/yourlabs
ln -sfn $PWD/tests/yourlabs/test ~/.ansible/collections/ansible_collections/yourlabs/test
ansible-playbook -i localhost, -c local $@ tests/test_ansible.yml
