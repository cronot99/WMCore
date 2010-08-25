#!/usr/bin/env python
"""
_WMBSMergeBySize_

Generic merging for WMBS.  This will correctly handle merging files that have
been split up honoring the original file boundaries.
"""

__revision__ = "$Id: WMBSMergeBySize.py,v 1.2 2009/04/09 16:41:58 sfoulkes Exp $"
__version__ = "$Revision: 1.2 $"

import threading

from WMCore.WMBS.File import File

from WMCore.DAOFactory import DAOFactory
from WMCore.JobSplitting.JobFactory import JobFactory
from WMCore.Services.UUID import makeUUID

def mergeUnitCompare(a, b):
    """
    _mergeUnitCompare_

    Compare two merge units.  They will be sorted first by run ID and then by
    lumi ID.
    """
    if a["run"] > b["run"]:
        return 1
    elif a["run"] == b["run"]:
        if a["lumi"] > b["lumi"]:
            return 1
        elif a["lumi"] == b["lumi"]:
            return 0
        else:
            return -1
    else:
        return -1

def fileCompare(a, b):
    """
    _fileCompare_

    Compare two files based on their "file_first_event" attribute.
    """
    if a["file_first_event"] > b["file_first_event"]:
        return 1
    if a["file_first_event"] == b["file_first_event"]:
        return 0
    else:
        return -1

def sortedFilesFromMergeUnits(mergeUnits):
    """
    _sortedFilesFromMergeUnits_

    Given a list of merge units sort them and the files that they contain.
    Return a list of sorted WMBS File structures.
    """
    mergeUnits.sort(mergeUnitCompare)

    sortedFiles = []
    for mergeUnit in mergeUnits:
        mergeUnit["files"].sort(fileCompare)

        for file in mergeUnit["files"]:
            newFile = File(id = file["file_id"], lfn = file["file_lfn"])
            sortedFiles.append(newFile)

    return sortedFiles

class WMBSMergeBySize(JobFactory):
    """
    _WMBSMergeBySize_

    Generic merging for WMBS.  This will correctly handle merging files that
    have been split up honoring the original file boundaries merging the files
    in the correct order.
    """
    def defineMergeUnits(self, mergeableFiles):
        """
        _defineMergeUnits_

        Split all the mergeable files into merge units.  A merge unit is a group
        of files that must be merged together.  For example, the files that
        result from event based splitting jobs need to be merged back together.
        This method will return a list of merge units.  A merge unit is a
        dictionary with the following keys: group_id, total_events, total_size,
        run, lumi, and files.  The files in the merge group are stored in a list
        under the files key.
        """
        mergeUnits = []

        for mergeableFile in mergeableFiles:
            newMergeFile = {}
            for key in mergeableFile.keys():
                newMergeFile[key] = mergeableFile[key]

            if mergeableFile["group_id"] != None:
                for mergeUnit in mergeUnits:
                    if mergeUnit["group_id"] == mergeableFile["group_id"]:
                        mergeUnit["files"].append(newMergeFile)
                        mergeUnit["total_size"] += newMergeFile["file_size"]
                        mergeUnit["total_events"] += newMergeFile["file_events"]

                        if mergeableFile["file_run"] < mergeUnit["run"] or \
                           (mergeableFile["file_run"] == mergeUnit["run"] and \
                            mergeableFile["file_lumi"] < mergeUnit["lumi"]):
                            newMergeUnit["run"] = newMergeFile["file_run"]
                            newMergeUnit["lumi"] = newMergeFile["file_lumi"]
                            
                        break
                else:
                    newMergeUnit = {}
                    newMergeUnit["group_id"] = newMergeFile["group_id"]
                    newMergeUnit["total_events"] = newMergeFile["file_events"]
                    newMergeUnit["total_size"] = newMergeFile["file_size"]
                    newMergeUnit["run"] = newMergeFile["file_run"]
                    newMergeUnit["lumi"] = newMergeFile["file_lumi"]
                    newMergeUnit["files"] = []
                    newMergeUnit["files"].append(newMergeFile)
                    mergeUnits.append(newMergeUnit)
            else:
                newMergeUnit = {}
                newMergeUnit["group_id"] = -1
                newMergeUnit["total_events"] = newMergeFile["file_events"]
                newMergeUnit["total_size"] = newMergeFile["file_size"]
                newMergeUnit["run"] = newMergeFile["file_run"]
                newMergeUnit["lumi"] = newMergeFile["file_lumi"]                
                newMergeUnit["files"] = []
                newMergeUnit["files"].append(newMergeFile)
                mergeUnits.append(newMergeUnit)

        return mergeUnits

    def createMergeJob(self, mergeUnits):
        """
        _createMergeJob_

        Create a merge job for the given merge units.  All the files contained
        in the merge units will be associated to the job.
        """
        newJob = self.jobInstance(name = makeUUID())
        sortedFiles = sortedFilesFromMergeUnits(mergeUnits)

        for file in sortedFiles:
            file.load()
            newJob.addFile(file)

        self.jobs.append(newJob)
        return
    
    def defineMergeJobs(self, mergeUnits):
        """
        _defineMergeJobs_

        Go through the list of merge units and try to combine them together into
        merge jobs that fit within the min/max filesizes and under the maximum
        number of events.  
        """
        mergeJobFileSize = 0
        mergeJobEvents = 0
        mergeJobFiles = []

        for mergeUnit in mergeUnits:
            if mergeUnit["total_size"] > self.maxMergeSize or \
                   mergeUnit["total_events"] > self.maxMergeEvents:
                self.createMergeJob([mergeUnit])
                continue
            elif mergeUnit["total_size"] + mergeJobFileSize > self.maxMergeSize or \
                     mergeUnit["total_events"] + mergeJobEvents > self.maxMergeEvents:
                if mergeJobFileSize > self.minMergeSize or \
                       self.forceMerge == True:
                    self.createMergeJob(mergeJobFiles)
                    mergeJobFileSize = 0
                    mergeJobEvents = 0
                    mergeJobFiles = []
                else:
                    continue
                    
            mergeJobFiles.append(mergeUnit)
            mergeJobFileSize += mergeUnit["total_size"]
            mergeJobEvents += mergeUnit["total_events"]
                        
        if mergeJobFileSize > self.minMergeSize or self.forceMerge == True:
            if len(mergeJobFiles) > 0:
                self.createMergeJob(mergeJobFiles)

        return
    
    def algorithm(self, groupInstance = None, jobInstance = None,
                  *args, **kwargs):
        """
        _algorithm_

        Try to merge any available files for the subscription provided.  This
        accepts the following keyword arguments:
          max_merge_size - The maximum size of merged files
          min_merge_size - The minimum size of merged files
          max_merge_events - The maximum number of events in a merge file
        """
        self.maxMergeSize = kwargs.get("max_merge_size", 1000000000)
        self.minMergeSize = kwargs.get("min_merge_size", 1048576)
        self.maxMergeEvents = kwargs.get("max_merge_events", 50000)
        self.jobs = []

        self.jobInstance = jobInstance
        self.groupInstance = groupInstance

        self.subscription["fileset"].load()

        if self.subscription["fileset"].open == True:
            self.forceMerge = False
        else:
            self.forceMerge = True

        myThread = threading.currentThread()
        daoFactory = DAOFactory(package = "WMCore.WMBS",
                                logger = myThread.logger,
                                dbinterface = myThread.dbi)
        
        mergeDAO = daoFactory(classname = "Subscriptions.GetFilesForMerge")
        mergeableFiles = mergeDAO.execute(self.subscription["id"])

        mergeUnits = self.defineMergeUnits(mergeableFiles)
        mergeUnits.sort(mergeUnitCompare)
        self.defineMergeJobs(mergeUnits)

        if len(self.jobs) == 0:
            return []

        jobGroup = groupInstance(subscription = self.subscription)
        jobGroup.add(self.jobs)
        jobGroup.commit()
        jobGroup.recordAcquire(list(self.jobs))
        
        return [jobGroup]
