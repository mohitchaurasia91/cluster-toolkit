# Copyright 2024 "Google LLC"
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Optional, Type

import pytest
from mock import Mock
from datetime import datetime, timezone, timedelta
import unittest

from common import TstNodeset, TstCfg # needed to import util
import util
from util import NodeState, MachineType, AcceleratorInfo, UpcomingMaintenance, InstanceResourceStatus, FutureReservation, ReservationDetails
from google.api_core.client_options import ClientOptions  # noqa: E402

# Note: need to install pytest-mock

@pytest.mark.parametrize(
    "name,expected",
    [
        (
            "az-buka-23",
            {
                "cluster": "az",
                "nodeset": "buka",
                "node": "23",
                "prefix": "az-buka",
                "range": None,
                "suffix": "23",
            },
        ),
        (
            "az-buka-xyzf",
            {
                "cluster": "az",
                "nodeset": "buka",
                "node": "xyzf",
                "prefix": "az-buka",
                "range": None,
                "suffix": "xyzf",
            },
        ),
        (
            "az-buka-[2-3]",
            {
                "cluster": "az",
                "nodeset": "buka",
                "node": "[2-3]",
                "prefix": "az-buka",
                "range": "[2-3]",
                "suffix": None,
            },
        ),
    ],
)
def test_node_desc(name, expected):
    assert util.lookup()._node_desc(name) == expected


@pytest.mark.parametrize(
    "name,expected",
    [
        ("az-buka-23", 23),
        ("az-buka-0", 0),
        ("az-buka", Exception),
        ("az-buka-xyzf", ValueError),
        ("az-buka-[2-3]", ValueError),
    ],
)
def test_node_index(name, expected):
    if  type(expected) is type and issubclass(expected, Exception):
        with pytest.raises(expected):
            util.lookup().node_index(name) 
    else:
        assert util.lookup().node_index(name) == expected


@pytest.mark.parametrize(
    "name",
    [
        "az-buka",
    ],
)
def test_node_desc_fail(name):
    with pytest.raises(Exception):
        util.lookup()._node_desc(name)


@pytest.mark.parametrize(
    "names,expected",
    [
        ("pedro,pedro-1,pedro-2,pedro-01,pedro-02", "pedro,pedro-[1-2,01-02]"),
        ("pedro,,pedro-1,,pedro-2", "pedro,pedro-[1-2]"),
        ("pedro-8,pedro-9,pedro-10,pedro-11", "pedro-[8-9,10-11]"),
        ("pedro-08,pedro-09,pedro-10,pedro-11", "pedro-[08-11]"),
        ("pedro-08,pedro-09,pedro-8,pedro-9", "pedro-[8-9,08-09]"),
        ("pedro-10,pedro-08,pedro-09,pedro-8,pedro-9", "pedro-[8-9,08-10]"),
        ("pedro-8,pedro-9,juan-10,juan-11", "juan-[10-11],pedro-[8-9]"),
        ("az,buki,vedi", "az,buki,vedi"),
        ("a0,a1,a2,a3,a4,a5,a6,a7,a8,a9,a10,a11,a12", "a[0-9,10-12]"),
        ("a0,a2,a4,a6,a7,a8,a11,a12", "a[0,2,4,6-8,11-12]"),
        ("seas7-0,seas7-1", "seas7-[0-1]"),
    ],
)
def test_to_hostlist(names, expected):
    assert util.to_hostlist(names.split(",")) == expected


@pytest.mark.parametrize(
    "api,ep_ver,expected",
    [
        (
            util.ApiEndpoint.BQ,
            "v1",
            ClientOptions(api_endpoint="https://bq.googleapis.com/v1/"),
        ),
        (
            util.ApiEndpoint.COMPUTE,
            "staging_v1",
            ClientOptions(api_endpoint="https://compute.googleapis.com/staging_v1/"),
        ),
        (
            util.ApiEndpoint.SECRET,
            "v1",
            ClientOptions(api_endpoint="https://secret_manager.googleapis.com/v1/"),
        ),
        (
            util.ApiEndpoint.STORAGE,
            "beta",
            ClientOptions(api_endpoint="https://storage.googleapis.com/beta/"),
        ),
        (
            util.ApiEndpoint.TPU,
            "alpha",
            ClientOptions(api_endpoint="https://tpu.googleapis.com/alpha/"),
        ),
    ],
)
def test_create_client_options(
    api: util.ApiEndpoint, ep_ver: str, expected: ClientOptions, mocker
):
    ud_mock = mocker.patch("util.universe_domain")
    ep_mock = mocker.patch("util.endpoint_version")
    ud_mock.return_value = "googleapis.com"
    ep_mock.return_value = ep_ver
    assert util.create_client_options(api).__repr__() == expected.__repr__()



@pytest.mark.parametrize(
        "nodeset,err",
        [
            (TstNodeset(reservation_name="projects/x/reservations/y"), AssertionError), # no zones
            (TstNodeset(
                reservation_name="projects/x/reservations/y",
                zone_policy_allow=["eine", "zwei"]), AssertionError), # multiples zones
            (TstNodeset(
                reservation_name="robin",
                zone_policy_allow=["eine"]), ValueError), # invalid name
            (TstNodeset(
                reservation_name="projects/reservations/y",
                zone_policy_allow=["eine"]), ValueError), # invalid name
            (TstNodeset(
                reservation_name="projects/x/zones/z/reservations/y",
                zone_policy_allow=["eine"]), ValueError), # invalid name
        ]
)
def test_nodeset_reservation_err(nodeset, err):
    lkp = util.Lookup(TstCfg())
    lkp._get_reservation = Mock()
    with pytest.raises(err):
        lkp.nodeset_reservation(nodeset)
    lkp._get_reservation.assert_not_called() # type: ignore

@pytest.mark.parametrize(
        "nodeset,policies,expected",
        [
            (TstNodeset(), [], None), # no reservation
            (TstNodeset(
                reservation_name="projects/bobin/reservations/robin",
                zone_policy_allow=["eine"]),
                [],
                util.ReservationDetails(
                    project="bobin",
                    zone="eine",
                    name="robin",
                    policies=[],
                    deployment_type=None,
                    reservation_mode=None,
                    bulk_insert_name="projects/bobin/reservations/robin")),
            (TstNodeset(
                reservation_name="projects/bobin/reservations/robin",
                zone_policy_allow=["eine"]),
                ["seven/wanders", "five/red/apples", "yum"],
                util.ReservationDetails(
                    project="bobin",
                    zone="eine",
                    name="robin",
                    policies=["wanders", "apples", "yum"],
                    deployment_type=None,
                    reservation_mode=None,
                    bulk_insert_name="projects/bobin/reservations/robin")),
            (TstNodeset(
                reservation_name="projects/bobin/reservations/robin/snek/cheese-brie-6",
                zone_policy_allow=["eine"]),
                [],
                util.ReservationDetails(
                    project="bobin",
                    zone="eine",
                    name="robin",
                    policies=[],
                    deployment_type=None,
                    reservation_mode=None,
                    bulk_insert_name="projects/bobin/reservations/robin/snek/cheese-brie-6")),

        ])

def test_nodeset_reservation_ok(nodeset, policies, expected):
    lkp = util.Lookup(TstCfg())
    lkp._get_reservation = Mock()

    if not expected:
        assert lkp.nodeset_reservation(nodeset) is None
        lkp._get_reservation.assert_not_called() # type: ignore
        return

    lkp._get_reservation.return_value = { # type: ignore
        "resourcePolicies": {i: p for i, p in enumerate(policies)},
    }
    assert lkp.nodeset_reservation(nodeset) == expected
    lkp._get_reservation.assert_called_once_with(expected.project, expected.zone, expected.name) # type: ignore

@pytest.mark.parametrize(
    "job_info,expected_job",
    [
        (
            """JobId=123
            TimeLimit=02:00:00
            JobName=myjob
            JobState=PENDING
            ReqNodeList=node-[1-10]""",
            util.Job(
                id=123,
                duration=timedelta(days=0, hours=2, minutes=0, seconds=0),
                name="myjob",
                job_state="PENDING",
                required_nodes="node-[1-10]"
            ),
        ),
        (
            """JobId=456
            JobName=anotherjob
            JobState=PENDING
            ReqNodeList=node-group1""",
            util.Job(
                id=456,
                duration=None,
                name="anotherjob",
                job_state="PENDING",
                required_nodes="node-group1"
            ),
        ),
        (
            """JobId=789
            TimeLimit=00:30:00
            JobState=COMPLETED""",
            util.Job(
                id=789,
                duration=timedelta(minutes=30),
                name=None,
                job_state="COMPLETED",
                required_nodes=None
            ),
        ),
        (
            """JobId=101112
            TimeLimit=1-00:30:00
            JobState=COMPLETED,
            ReqNodeList=node-[1-10],grob-pop-[2,1,44-77]""",
            util.Job(
                id=101112,
                duration=timedelta(days=1, hours=0, minutes=30, seconds=0),
                name=None,
                job_state="COMPLETED",
                required_nodes="node-[1-10],grob-pop-[2,1,44-77]"
            ),
        ),
        (
            """JobId=131415
            TimeLimit=1-00:30:00
            JobName=mynode-1_maintenance
            JobState=COMPLETED,
            ReqNodeList=node-[1-10],grob-pop-[2,1,44-77]""",
            util.Job(
                id=131415,
                duration=timedelta(days=1, hours=0, minutes=30, seconds=0),
                name="mynode-1_maintenance",
                job_state="COMPLETED",
                required_nodes="node-[1-10],grob-pop-[2,1,44-77]"
            ),
        ),
    ],
)
def test_parse_job_info(job_info, expected_job):
    lkp = util.Lookup(TstCfg())
    assert lkp._parse_job_info(job_info) == expected_job



@pytest.mark.parametrize(
    "node,state,want",
    [
        ("c-n-2", NodeState("DOWN", frozenset([])), NodeState("DOWN", frozenset([]))), # happy scenario
        ("c-d-vodoo", None, None), # dynamic nodeset
        ("c-x-44", None, None), # unknown(removed) nodeset
        ("c-n-7", None, None), # Out of bounds: c-n-[0-4] - downsized nodeset
        ("c-t-7", None, None), # Out of bounds: c-t-[0-4] - downsized nodeset TPU
        ("c-n-2", None, RuntimeError), # something is wrong
        ("c-t-2", None, RuntimeError), # something is wrong, but TPU
        
        # Check boundaries match [0-5)
        ("c-n-5", None, None), # out of boundaries
        ("c-n-4", None, RuntimeError), # within boundaries
    ])
def test_node_state(node: str, state: Optional[NodeState], want: NodeState | None | Type[Exception]):
    cfg = TstCfg(
        slurm_cluster_name="c",
        nodeset={
            "n": TstNodeset(node_count_static=2, node_count_dynamic_max=3)},
        nodeset_tpu={
            "t": TstNodeset(node_count_static=2, node_count_dynamic_max=3)},
        nodeset_dyn={
            "d": TstNodeset()},
    )
    lkp = util.Lookup(cfg)
    lkp.slurm_nodes = lambda: {node: state} if state else {} # type: ignore[assignment]
    # ... see https://github.com/python/typeshed/issues/6347    
        
    if  type(want) is type and issubclass(want, Exception):
        with pytest.raises(want):
            lkp.node_state(node)
    else:
        assert lkp.node_state(node) == want
        


@pytest.mark.parametrize(
    "jo,want",
    [
        ({
            "accelerators": [ { "guestAcceleratorCount": 1, "guestAcceleratorType": "nvidia-tesla-a100" } ],
            "creationTimestamp": "1969-12-31T16:00:00.000-08:00",
            "description": "Accelerator Optimized: 1 NVIDIA Tesla A100 GPU, 12 vCPUs, 85GB RAM",
            "guestCpus": 12,
            "id": "1000012",
            "imageSpaceGb": 0,
            "isSharedCpu": False,
            "kind": "compute#machineType",
            "maximumPersistentDisks": 128,
            "maximumPersistentDisksSizeGb": "263168",
            "memoryMb": 87040,
            "name": "a2-highgpu-1g",
            "selfLink": "https://www.googleapis.com/compute/v1/projects/io-playground/zones/us-central1-a/machineTypes/a2-highgpu-1g",
            "zone": "us-central1-a"
        }, MachineType(
            name="a2-highgpu-1g",
            guest_cpus=12,
            memory_mb=87040,
            accelerators=[
                AcceleratorInfo(type="nvidia-tesla-a100", count=1)
            ]
        )),
        ({
            "architecture": "X86_64",
            "creationTimestamp": "1969-12-31T16:00:00.000-08:00",
            "description": "8 vCPUs, 32 GB RAM",
            "guestCpus": 8,
            "id": "1210008",
            "imageSpaceGb": 0,
            "isSharedCpu": False,
            "kind": "compute#machineType",
            "maximumPersistentDisks": 128,
            "maximumPersistentDisksSizeGb": "263168",
            "memoryMb": 32768,
            "name": "t2d-standard-8",
            "selfLink": "https://www.googleapis.com/compute/v1/projects/io-playground/zones/europe-north2-b/machineTypes/t2d-standard-8",
            "zone": "europe-north2-b"
        }, MachineType(
            name="t2d-standard-8",
            guest_cpus=8,
            memory_mb=32768,
            accelerators=[]
        )),
    ])
def test_MachineType_from_json(jo: dict, want: MachineType):
    assert MachineType.from_json(jo) == want

UTC, PST = timezone.utc, timezone(timedelta(hours=-8))

@pytest.mark.parametrize(
    "got,want",
    [
        # from instance.creationTimestamp: 
        ("2024-11-30T12:47:51.676-08:00", datetime(2024, 11, 30, 12, 47, 51, 676000, tzinfo=PST)),
        # from futureReservation.creationTimestamp
        ("2024-11-05T15:23:33.702-08:00", datetime(2024, 11, 5, 15, 23, 33, 702000, tzinfo=PST)), 
        # from futureReservation.timeWindow.endTime
        ("2025-01-15T00:00:00Z", datetime(2025, 1, 15, 0, 0, tzinfo=UTC)),
        # fallback to UTC if no tz is specified
        ("2025-01-15T00:00:00", datetime(2025, 1, 15, 0, 0, tzinfo=UTC)),
    ])
def test_parse_gcp_timestamp(got: str, want: datetime):
    assert util.parse_gcp_timestamp(got) == want


@pytest.mark.parametrize(
    "got,want",
    [
        (None, None),
        (dict(
            windowStartTime="2025-01-15T00:00:00Z",
            somethingToIgnore="past failures",
        ), UpcomingMaintenance(window_start_time=datetime(2025, 1, 15, 0, 0, tzinfo=UTC))),
        (dict(
            startTimeWindow=dict(
                earliest="2025-01-15T00:00:00Z"),
            somethingToIgnore="past failures",
        ), UpcomingMaintenance(window_start_time=datetime(2025, 1, 15, 0, 0, tzinfo=UTC))),
        (dict(
            windowStartTime="2025-01-15T00:00:00Z",
            startTimeWindow=dict(
                earliest="2025-01-25T00:00:00Z"), # ignored
            somethingToIgnore="past failures",
        ), UpcomingMaintenance(window_start_time=datetime(2025, 1, 15, 0, 0, tzinfo=UTC))),
    ])
def tests_parse_UpcomingMaintenance_OK(got: dict, want: Optional[UpcomingMaintenance]):
    assert UpcomingMaintenance.from_json(got) == want


@pytest.mark.parametrize(
    "got",
    [
        {},
        dict(
            windowStartTime=dict(
                earliest="2025-01-15T00:00:00Z")),
    ])
def tests_parse_UpcomingMaintenance_FAIL(got: dict):
    with pytest.raises(ValueError):
            UpcomingMaintenance.from_json(got)


@pytest.mark.parametrize(
    "got,want",
    [
        (None,  InstanceResourceStatus(
            physical_host=None,
            upcoming_maintenance=None)),
        ({}, InstanceResourceStatus(
            physical_host=None,
            upcoming_maintenance=None)),
        (dict(
            physicalHost="/aaa/bbb/ccc"), 
        InstanceResourceStatus(
            physical_host="/aaa/bbb/ccc",
            upcoming_maintenance=None)),
        (dict(  # invalid upcomingMaintenance field to be ignored
            physicalHost="/aaa/bbb/ccc",
            upcomingMaintenance="maintenance is upon us"),
        InstanceResourceStatus(
            physical_host="/aaa/bbb/ccc",
            upcoming_maintenance=None)),
        (dict(
            physicalHost="/aaa/bbb/ccc",
            upcomingMaintenance=dict(windowStartTime="2025-01-15T00:00:00Z")), 
        InstanceResourceStatus(
            physical_host="/aaa/bbb/ccc",
            upcoming_maintenance=UpcomingMaintenance(
                window_start_time=datetime(2025, 1, 15, 0, 0, tzinfo=UTC)))),
    ])
def test_parse_InstanceResourceStatus(got: dict, want: Optional[InstanceResourceStatus]):
    assert InstanceResourceStatus.from_json(got) == want


def test_future_reservation_none():
    lkp = util.Lookup(TstCfg())
    assert lkp.future_reservation(TstNodeset()) == None


def test_future_reservation_declined():
    lkp = util.Lookup(TstCfg())
    lkp._get_future_reservation = Mock(return_value=dict(
        timeWindow = { "startTime": "2025-01-27T23:30:00Z", "endTime": "2025-02-03T23:30:00Z" },
        status = {"procurementStatus": "DECLINED"},
        reservationMode = "CALENDAR",
        specificReservationRequired = True,
    ))

    assert lkp.future_reservation(
        TstNodeset(future_reservation="projects/manhattan/zones/danger/futureReservations/zebra")) == FutureReservation(
            project='manhattan', 
            zone='danger', 
            name='zebra', 
            specific=True, 
            start_time=datetime(2025, 1, 27, 23, 30, tzinfo=timezone.utc), 
            end_time=datetime(2025, 2, 3, 23, 30, tzinfo=timezone.utc),
            reservation_mode="CALENDAR",
            active_reservation=None)
    lkp._get_future_reservation.assert_called_once_with("manhattan", "danger", "zebra")

@unittest.mock.patch('util.now', return_value=datetime(2025, 2, 13, 0, 0, tzinfo=timezone.utc))
def test_future_reservation_active(_):
    lkp = util.Lookup(TstCfg())
    lkp._get_future_reservation = Mock(return_value=dict(
        timeWindow = { "startTime": "2025-01-27T23:30:00Z", "endTime": "2025-02-21T23:30:00Z" },
        status = {
            "procurementStatus": "FULFILLED",
            "autoCreatedReservations": [
                "https://www.googleapis.com/compute/alpha/projects/manhattan/zones/danger/reservations/melon"
            ],
        },
        specificReservationRequired = True,
    ))
    lkp._get_reservation = Mock(return_value=dict())

    assert lkp.future_reservation(
        TstNodeset(future_reservation="projects/manhattan/zones/danger/futureReservations/zebra")) == FutureReservation(
            project='manhattan', 
            zone='danger', 
            name='zebra', 
            specific=True, 
            start_time=datetime(2025, 1, 27, 23, 30, tzinfo=timezone.utc), 
            end_time=datetime(2025, 2, 21, 23, 30, tzinfo=timezone.utc),
            reservation_mode=None, 
            active_reservation=ReservationDetails(
                project='manhattan',
                zone='danger',
                name='melon',
                policies=[],
                reservation_mode=None,
                bulk_insert_name="projects/manhattan/reservations/melon",
                deployment_type=None))
    
    lkp._get_future_reservation.assert_called_once_with("manhattan", "danger", "zebra")
    lkp._get_reservation.assert_called_once_with("manhattan", "danger", "melon")

@unittest.mock.patch('util.now', return_value=datetime(2025, 2, 28, 0, 0, tzinfo=timezone.utc))
def test_future_reservation_inactive(_):
    lkp = util.Lookup(TstCfg())
    lkp._get_future_reservation = Mock(return_value=dict(
        timeWindow = { "startTime": "2025-01-27T23:30:00Z", "endTime": "2025-02-21T23:30:00Z" },
        status = {
            "procurementStatus": "FULFILLED",
            "autoCreatedReservations": [
                "https://www.googleapis.com/compute/alpha/projects/manhattan/zones/danger/reservations/melon"
            ],
        },
        reservationMode = "DEFAULT",
        specificReservationRequired = True,
    ))
    lkp._get_reservation = Mock()

    assert lkp.future_reservation(
        TstNodeset(future_reservation="projects/manhattan/zones/danger/futureReservations/zebra")) == FutureReservation(
            project='manhattan', 
            zone='danger', 
            name='zebra', 
            specific=True, 
            start_time=datetime(2025, 1, 27, 23, 30, tzinfo=timezone.utc), 
            end_time=datetime(2025, 2, 21, 23, 30, tzinfo=timezone.utc), 
            reservation_mode="DEFAULT",
            active_reservation=None)
    
    lkp._get_future_reservation.assert_called_once_with("manhattan", "danger", "zebra")
    lkp._get_reservation.assert_not_called()
