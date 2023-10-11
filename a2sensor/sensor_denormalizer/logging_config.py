"""
a2sensor/sensor_denormalizer/logging_config.py

This script defines the LoggingConfig class.

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
import logging
import sys

class LoggingConfig:
    """
    Simple logging configuration utility.

    Class name: LoggingConfig

    Responsibilities:
        - Configures logging.

    Collaborators:
        - None
    """
    _instance = None

    def __init__(self, dateFormat:str="%Y-%m-%d %H:%M:%S %z"):
        """
        Creates a new LoggingConfig instance.
        """
        super().__init__()
        self._date_format = dateFormat

    @property
    def date_format(self):
        """
        Retrieves the date format.
        :return: Such format.
        :rtype: str
        """
        return self._date_format

    def configure_logging(self):
        """
        Configures the logging system.
        """
        level = logging.INFO
        default_logger = logging.getLogger()
        formatter = None
        for handler in logging.getLogger("gunicorn").handlers:
            formatter = handler.getFormatter()
            break
        if formatter is None:
            formatter = logging.Formatter(
                "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
                datefmt=self.date_format,
            )

        handlers_to_remove = []
        for handler in default_logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handlers_to_remove.append(handler)
        for handler in handlers_to_remove:
            default_logger.removeHandler(handler)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        default_logger.setLevel(level)
        default_logger.addHandler(console_handler)
        for handler in default_logger.handlers:
            handler.setFormatter(formatter)
        default_level = default_logger.getEffectiveLevel()

        a2sensor_logger = logging.getLogger("a2sensor")
        a2sensor_logger.setLevel(level)
        for handler in a2sensor_logger.handlers:
            handler.setFormatter(formatter)

    @classmethod
    def instance(cls):
        """
        Retrieves the singleton instance.
        :return: Such instance.
        :rtype: a2sensor.sensor_collect.Server
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

LoggingConfig.instance().configure_logging()
