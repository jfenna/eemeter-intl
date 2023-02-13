#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

   Copyright 2014-2023 OpenEEmeter contributors

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

"""
__all__ = ("EEMeterWarning",)


class EEMeterWarning(object):
    """An object representing a warning and data associated with it.

    Attributes
    ----------
    qualified_name : :any:`str`
        Qualified name, e.g., `'eemeter.method_abc.missing_data'`.
    description : :any:`str`
        Prose describing the nature of the warning.
    data : :any:`dict`
        Data that reproducibly shows why the warning was issued. Data should
        be JSON serializable.
    """

    def __init__(self, qualified_name, description, data):
        self.qualified_name = qualified_name
        self.description = description
        self.data = data

    def __repr__(self):
        return "EEMeterWarning(qualified_name={})".format(self.qualified_name)

    def json(self):
        """Return a JSON-serializable representation of this result.

        The output of this function can be converted to a serialized string
        with :any:`json.dumps`.
        """
        return {
            "qualified_name": self.qualified_name,
            "description": self.description,
            "data": self.data,
        }
