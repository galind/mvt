# Mobile Verification Toolkit (MVT) - Private
# Copyright (c) 2021-2022 Claudio Guarnieri.
# This file is part of MVT Private and its content is confidential.
# Please refer to the project maintainers before sharing with others.

import getpass
import logging
from typing import Optional

from mvt.android.parsers.backup import (AndroidBackupParsingError,
                                        InvalidBackupPassword, parse_ab_header,
                                        parse_backup_file, parse_tar_for_sms)

from .base import AndroidQFModule


class SMS(AndroidQFModule):
    """This module analyse SMS file in backup"""

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        fast_mode: Optional[bool] = False,
        log: logging.Logger = logging.getLogger(__name__),
        results: Optional[list] = None
    ) -> None:
        super().__init__(file_path=file_path, target_path=target_path,
                         results_path=results_path, fast_mode=fast_mode,
                         log=log, results=results)

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for message in self.results:
            if "body" not in message:
                continue

            if self.indicators.check_domains(message["links"]):
                self.detected.append(message)

    def parse_backup(self, data):
        header = parse_ab_header(data)
        if not header["backup"]:
            self.log.critical("Invalid backup format, backup.ab was not analysed")
            return

        password = None
        if header["encryption"] != "none":
            password = getpass.getpass(prompt="Backup Password: ", stream=None)
        try:
            tardata = parse_backup_file(data, password=password)
        except InvalidBackupPassword:
            self.log.critical("Invalid backup password")
            return
        except AndroidBackupParsingError:
            self.log.critical("Impossible to parse this backup file, please use"
                              " Android Backup Extractor instead")
            return

        if not tardata:
            return

        try:
            self.results = parse_tar_for_sms(tardata)
        except AndroidBackupParsingError:
            self.log.info("Impossible to read SMS from the Android Backup, "
                          "please extract the SMS and try extracting it with "
                          "Android Backup Extractor")
            return

    def run(self) -> None:
        files = self._get_files_by_pattern("*/backup.ab")
        if not files:
            self.log.info("No backup data found")
            return

        with open(files[0], "rb") as handle:
            data = handle.read()

        self.parse_backup(data)
        self.log.info("Identified %d SMS in backup data",
                      len(self.results))
