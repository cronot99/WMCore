#!/usr/bin/env python
"""
_SetLocationForWorkQueue_

MySQL implementation of Files.SetLocationForWorkQueue

For WorkQueue only
"""

from WMCore.Database.DBFormatter import DBFormatter

class SetLocationForWorkQueue(DBFormatter):
    """
    _SetLocationForWorkQueue_

    Set the location for a file, deleting all previous references
    and attaching the current references
    """

    deleteSQL = """DELETE FROM wmbs_file_location
                     WHERE fileid = (SELECT wfd.id FROM wmbs_file_details wfd WHERE wfd.lfn = :lfn)"""

    insertSQL = """INSERT IGNORE INTO wmbs_file_location (fileid, location)
                     SELECT wmbs_file_details.id, wls.location
                       FROM wmbs_location_pnns wls, wmbs_file_details
                       WHERE wls.pnn = :location
                       AND wmbs_file_details.lfn = :lfn"""


    def execute(self, lfns, locations, isDBS = True, conn = None, transaction = None):
        """
        If files are from DBS:
        First, delete all file_location references with that lfn.
        Then, insert the new ones.

        Else:
        Simply insert the new locations
        """
        binds = []
        for lfn in lfns:
            binds.append({'lfn': lfn})

        if isDBS:
            self.dbi.processData(self.deleteSQL, binds, conn = conn,
                                 transaction = transaction)

        self.dbi.processData(self.insertSQL, locations, conn = conn,
                             transaction = transaction)
        return
