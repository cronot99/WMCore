#!/usr/bin/env python
"""
_GetCountByState_

MySQL implementation of GetCountByState
"""

from WMCore.Database.DBFormatter import DBFormatter


class GetCountByState(DBFormatter):
    """
    Retrieve the number of wmbs jobs in a given state

    Returns an integer value.
    """
    sql = """
          SELECT count(*) FROM wmbs_job
              WHERE state = (SELECT id FROM wmbs_job_state WHERE name = :state)
          """

    def execute(self, state, conn=None, transaction=False):
        result = self.dbi.processData(self.sql, {'state': state},
                                      conn=conn,
                                      transaction=transaction)
        result = self.formatDict(result)

        return result[state]
