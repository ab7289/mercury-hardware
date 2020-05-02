from django.test import SimpleTestCase
from unittest.mock import patch, MagicMock, call

# from testfixtures import TempDirectory, LogCapture

import os
import sys
import json

sys.modules[
    "sense_hat"
] = MagicMock()  # mock these modules so that they don't have to be installed
sys.modules["sense_emu"] = MagicMock()

from hardware import main  # noqa : E402
from hardware.CommunicationsPi.comm_pi import CommPi  # noqa : E402


@patch("hardware.main.Transceiver")
@patch("hardware.main.WebClient")
@patch("hardware.main.SensePi")
@patch("hardware.main.GPSReader")
class HardwareTests(SimpleTestCase):
    @patch("hardware.main.handleComm")
    def test_main_comm_pi(
        self,
        com_mock=MagicMock(),
        mock_gps=MagicMock(),
        mock_sense=MagicMock(),
        mock_web=MagicMock(),
        mock_trans=MagicMock(),
    ):
        with patch.dict(os.environ, {"HARDWARE_TYPE": "commPi"}):
            main.main()
            com_mock.assert_called_once()

    @patch("hardware.main.handleSense")
    def test_main_sense_pi(
        self,
        sense_mock=MagicMock(),
        mock_gps=MagicMock(),
        mock_sense=MagicMock(),
        mock_web=MagicMock(),
        mock_trans=MagicMock(),
    ):
        with patch.dict(os.environ, {"HARDWARE_TYPE": "sensePi"}):
            main.main()
            sense_mock.assert_called_once()

    @patch("hardware.main.handleGps")
    def test_main_gps_pi(
        self,
        gps_mock=MagicMock(),
        mock_gps=MagicMock(),
        mock_sense=MagicMock(),
        mock_web=MagicMock(),
        mock_trans=MagicMock(),
    ):
        with patch.dict(os.environ, {"HARDWARE_TYPE": "gpsPi"}):
            main.main()
            gps_mock.assert_called_once()

    @patch("hardware.main.handleLocal")
    def test_main_local(
        self,
        local_mock=MagicMock(),
        mock_gps=MagicMock(),
        mock_sense=MagicMock(),
        mock_web=MagicMock(),
        mock_trans=MagicMock(),
    ):
        with patch.dict(os.environ, {"HARDWARE_TYPE": ""}):
            main.main()
            local_mock.assert_called_once()

    @patch("hardware.main.runServer")
    def test_handle_comm(
        self,
        server_mock=MagicMock(),
        mock_gps=MagicMock(),
        mock_sense=MagicMock(),
        mock_web=MagicMock(),
        mock_trans=MagicMock(),
    ):
        main.handleComm()
        server_mock.assert_called_once_with(handler_class=CommPi)

    @patch("time.sleep")
    def test_handle_sense(
        self,
        sleep_mock=MagicMock(),
        mock_gps=MagicMock(),
        mock_sense=MagicMock(),
        mock_web=MagicMock(),
        mock_trans=MagicMock(),
    ):
        # allow the time.sleep method to be called 5 times before throwing an error
        # this allows us to check that the data is being sent, but prevents it from
        # iterating forever
        sleep_mock.side_effect = ErrorAfter(5)

        expected_sensor_keys = {
            "temperature": 2,
            "pressure": 3,
            "humidity": 4,
            "acceleration": 5,
            "orientation": 6,
        }

        temp_data = {"key": "temp"}
        pres_data = {"key": "pres"}
        hum_data = {"key": "hum"}
        acc_data = {"key": "acc"}
        orient_data = {"key": "orient"}
        all_data = {"key": "all"}

        mock_sense.return_value.get_temperature.return_value = temp_data
        mock_sense.return_value.get_pressure.return_value = pres_data
        mock_sense.return_value.get_humidity.return_value = hum_data
        mock_sense.return_value.get_acceleration.return_value = acc_data
        mock_sense.return_value.get_orientation.return_value = orient_data
        mock_sense.return_value.get_all.return_value = all_data

        send_data_mock = MagicMock()
        mock_web.return_value.ping_lan_server = send_data_mock

        with self.assertRaises(Exception):
            main.handleSense()

        mock_sense.assert_called_with(sensor_ids=expected_sensor_keys)  # assert init
        mock_web.assert_called()  # assert init

        self.assertEqual(6, send_data_mock.call_count)
        send_data_mock.assert_has_calls(
            [
                call(json.dumps(temp_data)),
                call(json.dumps(pres_data)),
                call(json.dumps(hum_data)),
                call(json.dumps(acc_data)),
                call(json.dumps(orient_data)),
                call(json.dumps(all_data)),
            ],
            any_order=True,
        )

    def test_handle_sense_with_exception(
        self,
        mock_gps=MagicMock(),
        mock_sense=MagicMock(),
        mock_web=MagicMock(),
        mock_trans=MagicMock(),
    ):
        expected_sensor_keys = {
            "temperature": 2,
            "pressure": 3,
            "humidity": 4,
            "acceleration": 5,
            "orientation": 6,
        }

        temp_data = {"key": "temp"}
        pres_data = {"key": "pres"}
        hum_data = {"key": "hum"}
        acc_data = {"key": "acc"}
        orient_data = {"key": "orient"}
        all_data = {"key": "all"}

        mock_sense.return_value.get_temperature.return_value = temp_data
        mock_sense.return_value.get_pressure.return_value = pres_data
        mock_sense.return_value.get_humidity.return_value = hum_data
        mock_sense.return_value.get_acceleration.return_value = acc_data
        mock_sense.return_value.get_orientation.return_value = orient_data
        mock_sense.return_value.get_all.return_value = all_data

        mock_web.return_value.ping_lan_server.side_effect = CallableExhausted(
            "exhausted"
        )

        with self.assertRaises(Exception):
            main.handleSense()

        mock_sense.assert_called_with(sensor_ids=expected_sensor_keys)  # assert init
        mock_web.assert_called()  # assert init

    @patch("time.sleep")
    def test_handle_gps(
        self,
        sleep_mock=MagicMock(),
        mock_gps=MagicMock(),
        mock_sense=MagicMock(),
        mock_web=MagicMock(),
        mock_trans=MagicMock(),
    ):
        sleep_mock.side_effect = ErrorAfter(0)

        gps_data = {"key": "gps"}

        mock_gps.return_value.get_geolocation.return_value = gps_data

        send_data_mock = MagicMock()
        mock_web.return_value.ping_lan_server = send_data_mock

        with self.assertRaises(CallableExhausted):
            main.handleGps()

        mock_gps.assert_called_once()  # assert init
        mock_web.assert_called_once()  # assert init
        self.assertEquals(1, send_data_mock.call_count)
        send_data_mock.assert_has_calls([call(json.dumps(gps_data))], any_order=True)

    def test_handle_gps_with_exception(
        self,
        mock_gps=MagicMock(),
        mock_sense=MagicMock(),
        mock_web=MagicMock(),
        mock_trans=MagicMock(),
    ):
        gps_data = {"key": "gps"}

        mock_gps.return_value.get_geolocation.return_value = gps_data

        mock_web.return_value.ping_lan_server.side_effect = Exception("ex")

        with self.assertRaises(Exception):
            main.handleGps()

        mock_gps.assert_called_once()  # assert init
        mock_web.assert_called_once()  # assert init


class ErrorAfter(object):
    """
    Callable that will raise `CallableExhausted`
    exception after `limit` calls
    """

    def __init__(self, limit):
        self.limit = limit
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        if self.calls > self.limit:
            raise CallableExhausted()


class CallableExhausted(Exception):
    pass
