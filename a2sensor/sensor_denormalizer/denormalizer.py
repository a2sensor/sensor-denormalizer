"""
a2sensor/sensor_denormalizer/denormalizer.py

This script defines the Denormalizer class.

Copyright (C) 2023-today a2sensor's a2sensor/sensor_denormalizer

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import argparse
from datetime import datetime
import json
import logging
import os
import threading
import time
import toml
from typing import Dict, List


class Denormalizer:
    """
    Represents a Denormalizer, which manages a file with the most recent measure from sensors.

    Class name: Denormalizer

    Responsibilities:
        - Update the file with the most recent measure from sensors.

    Collaborators:
        - a2sensor.sensor_collect.Server: To generate measure files for each sensor.
    """

    def __init__(self, storageFolder: str, refreshInterval:int, outputFile: str, configFile: str):
        """
        Creates a new Denormalizer instance.
        :param storageFolder: The folder to store measures.
        :type storageFolder: str
        :param refreshInterval: The interval in minutes after which the output file gets refreshed.
        :type refreshInterval: int
        :param outputFile: The output sensors.json file.
        :type outputFile: str
        :param configFile: The configuration file.
        :type configFile: str
        """
        super().__init__()
        self._sensors = {}
        self._storage_folder = storageFolder
        self._refresh_interval = refreshInterval
        self._output_file = outputFile
        self._config_file = configFile
        self._exit_event = threading.Event()
        self.configure()

    @property
    def sensors(self) -> Dict:
        """
        Retrieves the configuration of the sensors.
        :return: Such settings.
        :rtype: Dict
        """
        return self._sensors

    @property
    def storage_folder(self):
        """
        Retrieves the storage folder.
        :return: Such value.
        :rtype: str
        """
        return self._storage_folder

    @property
    def refresh_interval(self):
        """
        Retrieves the refresh interval.
        :return: Such value.
        :rtype: int
        """
        return self._refresh_interval

    @property
    def output_file(self):
        """
        Retrieves the output file.
        :return: Such value.
        :rtype: str
        """
        return self._output_file

    @property
    def config_file(self):
        """
        Retrieves the config file.
        :return: Such value.
        :rtype: str
        """
        return self._config_file

    @property
    def exit_event(self):
        """
        Retrieves the exit event.
        :return: Such event.
        :rtype: threading.Event
        """
        return self._exit_event

    def configure(self):
        """
        Reads the settings from the configuration file.
        """
        config = toml.load(self.config_file)

        index = 0
        for sensor, attributes in config.items():
            attributes["index"] = index
            index = index + 1
            self.sensors[sensor] = attributes

    def list_sensors(self) -> List:
        """
        Retrieves the list of sensors.
        :return: Such list.
        :rtype: List
        """
        return self.list_subfolders(self.storage_folder)

    def list_subfolders(self, path):
        """
        Lists all subfolders under a given path.
        :param path: Path to the directory.
        :return: List of subfolder names.
        """
        entries = os.listdir(path)

        # Filter out entries that are directories
        return [entry for entry in entries if os.path.isdir(os.path.join(path, entry))]

    def latest_measure_file(self, sensorId: str) -> str:
        """
        Retrieves the file with the most recent measure for given sensor.
        :param sensorId: The id of the sensor.
        :type sensorId: str
        :return: The file with the latest measure.
        :rtype: str
        """
        directory = os.path.join(self.storage_folder, sensorId)
        if os.path.exists(directory):
            files = [ os.path.join(directory, f) for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f)) ]
            result = max(files, key=os.path.basename)
        else:
            result = None

        return result

    def latest_measure(self, sensorId: str) -> Dict:
        """
        Retrieves the latest measure for given sensor.
        :param sensorId: The id of the sensor.
        :type sensorId: str
        :return: The latest measure.
        :rtype: Dict
        """
        result = {}
        measure_file = self.latest_measure_file(sensorId)
        if measure_file:
            with open(measure_file, "r") as file:
                result = json.load(file)
        else:
            result['id'] = sensorId
            result['name'] = self.sensors[sensorId]['name']
            value = {}
            value['status'] = 'unknown'
            value['timestamp'] = self.format_date(datetime.now())
            result['value'] = value

        return result

    def save_output_file(self, data: Dict):
        """
        Saves given measure to disk.
        :param sensorId: The id of the sensor.
        :type sensorId: str
        :param data: The measure.
        :type data: Dict
        """
        with open(self.output_file, "w") as file:
            json.dump(data, file)

    def format_date(self, date) -> str:
        """
        Retrieves the timestamp of the current time.
        :param date: The date.
        :type date: datetime.datetime
        :return: Such timestamp.
        :rtype: str
        """
        from .logging_config import LoggingConfig
        return date.strftime(LoggingConfig.instance().date_format)

    def refresh_output_file(self):
        """
        Refreshes the output file.
        """
        sensors_data = []
        sensors_refreshed = 0
        now = datetime.now()
        timestamp = self.format_date(now)

        for sensorId in self.sensors:
            data = {}
            data["id"] = sensorId
            data["name"] = self.sensors[sensorId]["name"]
            if self.sensors[sensorId].get("pin", -1) == -1:
                data["value"] = {"status": "unknown", "timestamp": timestamp}
            else:
                sensors_refreshed = sensors_refreshed + 1
                measure = self.latest_measure(sensorId)
                value = measure.get("value", {})
                status = value.get("status", None)
                last_modified = value.get("timestamp", None)
                if status is not None and last_modified is not None:
                    data["value"] = value
                    del measure["value"]
                else:
                    data["value"] = measure
            sensors_data.append(data)

        if sensors_refreshed > 0:
            self.save_output_file(sensors_data)
            logging.getLogger("a2sensor").info(
                f'Refreshed {sensors_refreshed} sensors in {self.output_file} at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
            )

    def run(self):
        try:
            while not self.exit_event.is_set():
                self.refresh_output_file()
                time.sleep(self.refresh_interval)
        except KeyboardInterrupt:
            logging.getLogger("a2sensor").warning("Exiting")
            self.exit_event.set()


def parse_cli():
    """
    Parses the command-line arguments.
    :return: The Denormalizer instance.
    :rtype: a2sensor.sensor_denormalizer.Denormalizer
    """
    parser = argparse.ArgumentParser(description="Runs A2Sensor Sensor-Denormalizer")
    parser.add_argument(
        "-d",
        "--data-folder",
        required=True,
        help="The data folder used by A2Sensor Sensor-Collect",
    )
    parser.add_argument('-r', '--refresh-interval', required=False, default=1, help='The refresh interval, in seconds')
    parser.add_argument("-o", "--output-file", required=True, help="The output file")
    parser.add_argument(
        "-c", "--config-file", required=True, help="The sensors.toml config file"
    )
    args, unknown_args = parser.parse_known_args()
    return Denormalizer(args.data_folder, int(args.refresh_interval), args.output_file, args.config_file)


if __name__ == "__main__":
    denormalizer = parse_cli()
    denormalizer.run()
