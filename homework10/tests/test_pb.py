import os
import unittest
import gzip
import struct
import deviceapps_pb2

import pb

MAGIC = 0xFFFFFFFF
DEVICE_APPS_TYPE = 1
TEST_FILE = "test.pb.gz"


class TestPB(unittest.TestCase):
    deviceapps = [
        {"device": {"type": "idfa", "id": "e7e1a50c0ec2747ca56cd9e1558c0d7c"},
         "lat": 67.7835424444, "lon": -22.8044005471, "apps": [1, 2, 3, 4]},
        {"device": {"type": "gaid", "id": "e7e1a50c0ec2747ca56cd9e1558c0d7d"}, "lat": 42, "lon": -42, "apps": [1, 2]},
        {"device": {"type": "gaid", "id": "e7e1a50c0ec2747ca56cd9e1558c0d7d"}, "lat": 42, "lon": -42, "apps": []},
        {"device": {"type": "gaid", "id": "e7e1a50c0ec2747ca56cd9e1558c0d7d"}, "apps": [1]},
    ]

    def tearDown(self):
        os.remove(TEST_FILE)

    def test_write(self):
        bytes_written = pb.deviceapps_xwrite_pb(self.deviceapps, TEST_FILE)
        self.assertTrue(bytes_written > 0)
        with gzip.open(TEST_FILE) as f:
            for deviceapp in self.deviceapps:
                # Test header
                header = f.read(8) # uint32 + 2 * uint16 (arch depend)
                magic, dev_apps_type, length = struct.unpack('<IHH', header)
                self.assertEqual(magic, MAGIC)
                self.assertEqual(dev_apps_type, DEVICE_APPS_TYPE)

                # Test unpacked data
                packed = f.read(length)
                unpacked = deviceapps_pb2.DeviceApps()
                unpacked.ParseFromString(packed)
                self.assertEqual(unpacked.device.type,
                    deviceapp['device']['type'])
                self.assertEqual(unpacked.device.id,
                    deviceapp['device']['id'])
                self.assertEqual(unpacked.HasField('lat'),
                    'lat' in deviceapp)
                self.assertEqual(unpacked.HasField('lon'),
                    'lon' in deviceapp)
                if unpacked.HasField('lat'):
                    self.assertEqual(unpacked.lat, deviceapp['lat'])
                if unpacked.HasField('lon'):
                    self.assertEqual(unpacked.lon, deviceapp['lon'])
                self.assertEqual(unpacked.apps, deviceapp['apps'])

    @unittest.skip("Optional problem")
    def test_read(self):
        pb.deviceapps_xwrite_pb(self.deviceapps, TEST_FILE)
        for i, d in pb.deviceapps_xread_pb(TEST_FILE):
            self.assertEqual(d, self.deviceapps[i])
