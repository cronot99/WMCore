#!/usr/bin/env python





"""
MySQL implementation of AddFile
"""
from WMCore.Database.DBFormatter import DBFormatter

class Add(DBFormatter):

    sql = """insert into dbsbuffer_file(lfn, filesize, events, dataset_algo, status, workflow, in_phedex)
                values (:lfn, :filesize, :events, :dataset_algo, :status, :workflow, :in_phedex)"""

    def getBinds(self, files, size, events, cksum, dataset_algo, status, workflowID, inPhedex):
        # Can't use self.dbi.buildbinds here...
        binds = {}
        if isinstance(files, basestring):
            binds = {'lfn': files,
                     'filesize': size,
                     'events': events,
                     'dataset_algo': dataset_algo,
                     'status' : status,
                     'workflow': workflowID,
                     'in_phedex': inPhedex}
        elif isinstance(files, list):
        # files is a list of tuples containing lfn, size, events, cksum, dataset, status
            binds = []
            for f in files:
                binds.append({'lfn': f[0],
                              'filesize': f[1],
                              'events': f[2],
                              'dataset_algo': f[3],
                              'status' : f[4],
                              'workflow': f[5],
                              'in_phedex': f[6]})
        return binds

    def execute(self, files = None, size = 0, events = 0, cksum = 0,
                datasetAlgo = 0, status = "NOTUPLOADED", workflowID = None,
                inPhedex=0, conn = None, transaction = False):
        binds = self.getBinds(files, size, events, cksum, datasetAlgo, status,
                              workflowID, inPhedex)

        self.dbi.processData(self.sql, binds, conn=conn, transaction=transaction)

        return
