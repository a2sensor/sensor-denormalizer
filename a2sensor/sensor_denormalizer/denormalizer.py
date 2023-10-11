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
from apscheduler.schedulers.background import BackgroundScheduler
import argparse
from datetime import datetime
import json
import logging
import os
import threading
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

    def __init__(self, storageFolder: str, refreshInterval:int, sensorsFile: str):
        """
        Creates a new Denormalizer instance.
        :param storageFolder: The folder to store measures.
        :type storageFolder: str
        :param refreshInterval: The interval in minutes after which the output file gets refreshed.
        :type refreshInterval: int
        :param sensorsFile: The global sensors.json file.
        :type sensorsFile: str
        """
        super().__init__()
        self._storage_folder = storageFolder
        self._refresh_interval = refreshInterval
        self._sensors_file = sensorsFile

        self._scheduler = self.init_scheduler(self._refresh_interval)

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
    def sensors_file(self):
        """
        Retrieves the sensors.json file.
        :return: Such value.
        :rtype: str
        """
        return self._sensors_file

    @property
    def scheduler(self):
        """
        Retrieves the scheduler.
        :return: Such instance.
        :rtype: apscheduler.schedulers.background.BackgroundScheduler
        """
        return self._scheduler

    def init_scheduler(self, refreshInterval: int):
        """
        Initializes the scheduler.
        :param refreshInterval: The interval in minutes after which the output file gets refreshed.
        :type refreshInterval: int
        :return: The background scheduler.
        :rtype: apscheduler.schedulers.background.BackgroundScheduler
        """
        result = BackgroundScheduler()
        result.add_job(self.refresh_output_file, "interval", minutes=refreshInterval)
        return result

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
        files = [os.path.join(directory, f) for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
        return max(files, key=os.path.basename)

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
        with open(measure_file, 'r') as file:
            result = json.load(file)
        return result

    def save_output_file(self, data: Dict):
        """
        Saves given measure to disk.
        :param sensorId: The id of the sensor.
        :type sensorId: str
        :param data: The measure.
        :type data: Dict
        """
        with open(self.sensors_file, "w") as file:
            json.dump(data, file)

    def refresh_output_file(self):
        """
        Refreshes the output file.
        """
        sensors_data = []
        some_data = False
        for sensorId in self.list_sensors():
            data = {}
            some_data = True
            data['id'] = sensorId
            measure = self.latest_measure(sensorId)
            name = measure.get('name', None)
            value = measure.get('value', {})
            status = value.get('status', None)
            last_modified = value.get('timestamp', None)
            if name is not None:
                data['name'] = name
                del measure['name']
            if status is not None and last_modified is not None:
                data['value'] = value
                del measure['value']
            else:
                data['value'] = self.latest_measure(sensorId)
            sensors_data.append(data)

        if some_data:
            self.save_output_file(sensors_data)
            print(f'Refreshed {self.sensors_file} at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

    def run(self):
        self.refresh_output_file()
        self.scheduler.start()
        stop_event = threading.Event()

        try:
            stop_event.wait()
        except KeyboardInterrupt:
            logging.getLogger("a2sensor").warning("Shutting down gracefully...")
        finally:
            self.scheduler.shutdown()

def parse_cli():
    """
    Parses the command-line arguments.
    :return: The Denormalizer instance.
    :rtype: a2sensor.sensor_denormalizer.Denormalizer
    """
    parser = argparse.ArgumentParser(description="Runs A2Sensor Sensor-Denormalizer")
    parser.add_argument('-d', '--data-folder', required=True, help='The data folder used by A2Sensor Sensor-Collect')
    parser.add_argument('-r', '--refresh-interval', required=False, default=1, help='The refresh interval, in minutes')
    parser.add_argument('-o', '--output-file', required=True, help='The output file')
    args, unknown_args = parser.parse_known_args()
    return Denormalizer(args.data_folder, int(args.refresh_interval), args.output_file)

if __name__ == "__main__":
    denormalizer = parse_cli()
    denormalizer.run()
