# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import filecmp
import sys

duplicates = [
    [
        "modules/file-system/pre-existing-network-storage/scripts/mount.sh",
        "modules/file-system/filestore/scripts/mount.sh",
        "modules/file-system/managed-lustre/scripts/mount.sh",
        "community/modules/file-system/cloud-storage-bucket/scripts/mount.sh",
        "community/modules/file-system/nfs-server/scripts/mount.sh",
    ],
    [
        "community/modules/file-system/nfs-server/scripts/install-nfs-client.sh",
        "modules/file-system/filestore/scripts/install-nfs-client.sh",
        "modules/file-system/pre-existing-network-storage/scripts/install-nfs-client.sh",
    ],
    [
        "modules/file-system/pre-existing-network-storage/scripts/install-gcs-fuse.sh",
        "community/modules/file-system/cloud-storage-bucket/scripts/install-gcs-fuse.sh",
    ],
    [
        "modules/scheduler/batch-job-template/startup_from_network_storage.tf",
        "modules/compute/vm-instance/startup_from_network_storage.tf",
    ],
    [
        "modules/compute/gke-node-pool/threads_per_core_calc.tf",
        "modules/compute/vm-instance/threads_per_core_calc.tf",
    ],
    [
        "community/modules/scheduler/schedmd-slurm-gcp-v6-controller/source_image_logic.tf",
        "community/modules/scheduler/schedmd-slurm-gcp-v6-login/source_image_logic.tf",
        "community/modules/compute/schedmd-slurm-gcp-v6-nodeset/source_image_logic.tf",
        "community/modules/compute/schedmd-slurm-gcp-v6-nodeset-dynamic/source_image_logic.tf",
    ],
    [
        "community/modules/scripts/ramble-execute/templates/ramble_execute.yml.tpl",
        "community/modules/scripts/spack-execute/templates/execute_commands.yml.tpl",
    ],
    [
        "community/modules/scripts/spack-setup/templates/spack_setup.yml.tftpl",
        "community/modules/scripts/ramble-setup/templates/ramble_setup.yml.tftpl",
    ],
    [
        "community/modules/scripts/spack-setup/scripts/install_spack_deps.yml",
        "community/modules/scripts/ramble-setup/scripts/install_ramble_deps.yml",
    ],
    [
        "modules/file-system/parallelstore/scripts/install-daos-client.sh",
        "modules/file-system/pre-existing-network-storage/scripts/install-daos-client.sh",
    ],
    [
        "modules/file-system/parallelstore/templates/mount-daos.sh.tftpl",
        "modules/file-system/pre-existing-network-storage/templates/mount-daos.sh.tftpl",
    ],
    [
        "modules/compute/vm-instance/compute_image.tf"
        "modules/scheduler/batch-job-template/compute_image.tf"
        "community/modules/compute/htcondor-execute-point/compute_image.tf"
    ],
    [
        "modules/scheduler/gke-cluster/templates/gke-network-paramset.yaml.tftpl",
        "modules/scheduler/pre-existing-gke-cluster/templates/gke-network-paramset.yaml.tftpl",
    ],
    [
        "modules/scheduler/gke-cluster/templates/network-object.yaml.tftpl",
        "modules/scheduler/pre-existing-gke-cluster/templates/network-object.yaml.tftpl",
    ],
    [
        "modules/file-system/pre-existing-network-storage/scripts/install-managed-lustre-client.sh",
        "modules/file-system/managed-lustre/scripts/install-managed-lustre-client.sh"
    ]
]

for group in duplicates:
    first = group[0]
    for second in group[1:]:
        if not filecmp.cmp(first, second):  # true if files are the same
            print(f'found diff between {first} and {second}')
            sys.exit(1)
