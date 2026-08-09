#!/bin/bash
set -euo pipefail

dnf install -y python3 python3-pip
pip3 install --quiet boto3
systemctl enable --now amazon-ssm-agent
