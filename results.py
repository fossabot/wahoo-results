# Wahoo! Results - https://github.com/JohnStrunk/wahoo-results
# Copyright (C) 2020 - John D. Strunk
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
This file defines the result classes.
"""

import math
import re
from typing import List

class FileParseError(Exception):
    """Execption for when a file cannot be parsed."""
    def __init__(self, filename: str, error: str):
        """Create an exception."""
        self.filename = filename
        self.error = error
        super().__init__(self, filename, error)

def _truncate_hundredths(num: float) -> float:
    return math.floor(num * 100.0) / 100.0
    
class Event:
    """
    Event represents a swimming event.
    """
    event: str
    event_desc: str
    num_heats: int

    def from_scb(self, filename: str) -> None:
        file = open(filename, "r")
        lines = file.readlines()
        file.close()
        return self.from_lines(lines)

    def from_lines(self, lines: List[str]) -> None:
        match = re.match(r"^#(\w+)\s+(.*)$", lines[0])
        if not match:
            raise FileParseError("", "Unable to parse header")
        self.event = match.group(1)
        self.event_desc = match.group(2)
        self.num_heats = (len(lines)-1)//10


class Lane:
    """
    Lane is the result for a single lane of the heat.
    """
    name: str  # Swimmer's name
    team: str  # Swimmer's team
    times: List[float]  # List of individual measured times

    def __init__(self, **kwargs):
        self.name = kwargs.get("name", "")
        self.team = kwargs.get("team", "")
        self.times = kwargs.get("times", [])

    def is_empty(self) -> bool:
        """
        Returns True if the lane is believed to be empty.

        >>> Lane(times=[7.34, 7.12, 7.20]).is_empty()
        False
        >>> Lane().is_empty()
        True
        >>> Lane(name="One, Some").is_empty()
        False
        """
        return self.name == "" and len(self.times) == 0

    def times_are_valid(self) -> bool:
        """
        Returns True if all times are within 0.3 seconds.

        >>> Lane(times=[7.34, 7.12, 7.20]).times_are_valid()
        True
        >>> Lane(times=[7.34, 7.02, 7.20]).times_are_valid()
        False
        >>> Lane().times_are_valid()
        False
        """
        return len(self.times) > 0 and max(self.times) - min(self.times) <= 0.3

    def final_time(self) -> float:
        """
        Calculates the final time based on the individual times according to
        USA-S rules.

        >>> Lane(times=[7.0, 4.0, 6.2]).final_time()
        6.2
        >>> Lane(times=[7.0, 6.2]).final_time()
        6.6
        >>> Lane(times=[9.1]).final_time()
        9.1
        >>> Lane(times=[7.13, 6.1]).final_time()
        6.61
        """
        if len(self.times) == 3:
            self.times.sort()
            return self.times[1]
        if len(self.times) == 2:
            return _truncate_hundredths((self.times[0] + self.times[1]) / 2)
        if len(self.times) == 1:
            return self.times[0]
        return 0.0

    def dump(self):
        """
        Dumps the lane data to the screen.
        """
        print(f"Name: {self.name}")
        print(f"Team: {self.team}")
        print(f"Times: {self.times}")
        print(f"Final: {self.final_time()}")
        print(f"Valid: {self.times_are_valid()}")
        print(f"Empty: {self.is_empty()}")

class Heat:
    """
    Heat is the result of a single heat.

    Usage:
        # Create a Result object
        res = Result()
        # Load the CTS Dolphin timing results
        res.load_do4("016-129-004A-0054.do4")
        # Load the scoreboard data
        res.load_scb("E129.scb")
    """
    event: str  # Event number
    event_desc: str # Event description
    heat: int  # Heat number
    lanes: List[Lane]  # Lane information

    def __init__(self, **kwargs):
        self.event = kwargs.get("event", "")
        self.event_desc = kwargs.get("event_desc","")
        self.heat = kwargs.get("heat", 0)
        self.lanes = kwargs.get("lanes", [Lane() for i in range(0, 10)])

    def load_do4(self, filename: str) -> None:
        """
        Loads event results from a CTS Dolphin *.do4 file.
        """
        file = open(filename, "r")
        lines = file.readlines()
        file.close()
        try:
            self._parse_do4(lines)
        except FileParseError as err:
            raise FileParseError(filename, err.error)

    def _parse_do4(self, lines) -> None:
        # Ensure the file is the expected number of lines
        if len(lines) != 12:
            raise FileParseError("", "Unexpected number of lines")
        # Ensure the checksum is present
        if not re.match(r'^[0-9A-F]{16}$', lines[-1]):
            raise FileParseError("", "EOF checksum not found")
        # Extract the event & heat from the header
        match = re.match(r'^([^;]+);(\d+);1;.+$', lines[0])
        if not match:
            raise FileParseError("", "Unable to parse header")
        self.event = match.group(1)
        self.heat = int(match.group(2))
        # Parse the lane results
        for i in range(1, 11):
            fields = lines[i].strip().split(';')
            times = [_truncate_hundredths(float(x)) for x in fields[1:] if x != '' and x != '0']
            self.lanes[i-1].times = times

    def load_scb(self, filename: str) -> None:
        """
        Loads event data from a CTS start list *.scb file.
        Note: Heat should be set before calling this method.
        """
        file = open(filename, "r")
        lines = file.readlines()
        file.close()
        try:
            self._parse_scb(lines)
        except FileParseError as err:
            raise FileParseError(filename, err.error)

    def _parse_scb(self, lines) -> None:
        # Ensure file has the expected # of lines
        if (len(lines)-1) % 10 or len(lines) <= self.heat * 10:
            raise FileParseError("", "Unexpected number of lines in file")
        # Extract event name
        match = re.match(r'^#\w+\s+(.*)$', lines[0])
        if not match:
            raise FileParseError("", "Unable to parse event name")
        self.event_desc = match.group(1)
        # Parse heat names/teams
        heat_start = (self.heat - 1) * 10 + 1
        for i in range(0, 10):
            match = re.match(r'^(.*)--(.*)$', lines[heat_start + i])
            if not match:
                raise FileParseError("", "Unable to parse name/team")
            self.lanes[i].name = match.group(1).strip()
            self.lanes[i].team = match.group(2).strip()

    def num_expected_times(self) -> int:
        """
        Return the number of individual times that should be expected.
        """
        # We expect all lanes to have the same number of times, so return the
        # maximum across all lanes.
        return max([len(l.times) for l in self.lanes])

    def place(self, lane: int) -> int:
        """
        Return the place (1-n) for a given lane.
        """
        if not self.lanes[lane].times_are_valid():
            return 0
        time = self.lanes[lane].final_time()
        place = 1
        for i in self.lanes:
            if i.times_are_valid() and i.final_time() < time:
                place += 1
        return place

    def dump(self):
        """Dump the results to the screen."""
        print(f"Event: {self.event}")
        print(f"Event desc: {self.event_desc}")
        print(f"Heat: {self.heat}")
        for i in self.lanes:
            i.dump()