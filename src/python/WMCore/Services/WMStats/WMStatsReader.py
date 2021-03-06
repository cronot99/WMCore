from __future__ import division, print_function

from Utils.IteratorTools import nestedDictUpdate
from WMCore.Database.CMSCouch import CouchServer
from WMCore.Services.WMStats.DataStruct.RequestInfoCollection import RequestInfo
from WMCore.Lexicon import splitCouchServiceURL, sanitizeURL
from WMCore.Services.RequestDB.RequestDBReader import RequestDBReader

REQUEST_PROPERTY_MAP = {
    "_id": "_id",
    "InputDataset": "inputdataset",
    "PrepID": "prep_id",
    "Group": "group",
    "RequestDate": "request_date",
    "Campaign": "campaign",
    "RequestName": "workflow",
    "RequestorDN": "user_dn",
    "RequestPriority": "priority",
    "Requestor": "requestor",
    "RequestType": "request_type",
    "DbsUrl": "dbs_url",
    "CMSSWVersion": "cmssw",
    "OutputDatasets": "outputdatasets",
    "RequestTransition": "request_status",  # Status: status,  UpdateTime: update_time
    "SiteWhitelist": "site_white_list",
    "Teams": "teams",
    "TotalEstimatedJobs": "total_jobs",
    "TotalInputEvents": "input_events",
    "TotalInputLumis": "input_lumis",
    "TotalInputFiles": "input_num_files",
    "Run": "run",
    # Status and UpdateTime is under "RequestTransition"
    "Status": "status",
    "UpdateTime": "update_time"
}


def convertToLegacyFormat(requestDoc):
    converted = {}
    for key, value in requestDoc.items():

        if key == "RequestTransition":
            newValue = []
            for transDict in value:
                newItem = {}
                for transKey, transValue in transDict.items():
                    newItem[REQUEST_PROPERTY_MAP.get(transKey, transKey)] = transValue
                    newValue.append(newItem)
            value = newValue

        converted[REQUEST_PROPERTY_MAP.get(key, key)] = value

    return converted


class WMStatsReader(object):
    # TODO need to get this from reqmgr api
    ACTIVE_STATUS = ["new",
                     "assignment-approved",
                     "assigned",
                     "acquired",
                     "running",
                     "running-open",
                     "running-closed",
                     "failed",
                     "force-complete",
                     "completed",
                     "closed-out",
                     "announced",
                     "aborted",
                     "aborted-completed",
                     "rejected"]

    T0_ACTIVE_STATUS = ["new",
                        "Closed",
                        "Merge",
                        "Harvesting",
                        "Processing Done",
                        "AlcaSkim",
                        "completed"]

    def __init__(self, couchURL, appName="WMStats", reqdbURL=None, reqdbCouchApp="ReqMgr"):
        self._sanitizeURL(couchURL)
        # set the connection for local couchDB call
        self._commonInit(couchURL, appName)
        if reqdbURL:
            self.reqDB = RequestDBReader(reqdbURL, reqdbCouchApp)
        else:
            self.reqDB = None

    def _sanitizeURL(self, couchURL):
        return sanitizeURL(couchURL)['url']

    def _commonInit(self, couchURL, appName="WMStats"):
        """
        setting up comon variables for inherited class.
        inherited class should call this in their init function
        """

        self.couchURL, self.dbName = splitCouchServiceURL(couchURL)
        self.couchServer = CouchServer(self.couchURL)
        self.couchDB = self.couchServer.connectDatabase(self.dbName, False)
        self.couchapp = appName
        self.defaultStale = {"stale": "update_after"}

    def setDefaultStaleOptions(self, options):
        if not options:
            options = {}
        if 'stale' not in options:
            options.update(self.defaultStale)
        return options

    def getLatestJobInfoByRequests(self, requestNames):
        jobInfoByRequestAndAgent = {}

        if len(requestNames) > 0:
            requestAndAgentKey = self._getRequestAndAgent(requestNames)
            jobDocIds = self._getLatestJobInfo(requestAndAgentKey)
            jobInfoByRequestAndAgent = self._getAllDocsByIDs(jobDocIds)
        return jobInfoByRequestAndAgent

    def _updateRequestInfoWithJobInfo(self, requestInfo):
        if len(requestInfo.keys()) != 0:
            jobInfoByRequestAndAgent = self.getLatestJobInfoByRequests(requestInfo.keys())
            self._combineRequestAndJobData(requestInfo, jobInfoByRequestAndAgent)

    def _getCouchView(self, view, options, keys=None):
        keys = keys or []
        options = self.setDefaultStaleOptions(options)

        if keys and isinstance(keys, str):
            keys = [keys]
        return self.couchDB.loadView(self.couchapp, view, options, keys)

    def _formatCouchData(self, data, key="id"):
        result = {}
        for row in data['rows']:
            if 'error' in row:
                continue
            if "doc" in row:
                result[row[key]] = row["doc"]
            else:
                result[row[key]] = None
        return result

    def _combineRequestAndJobData(self, requestData, jobData):
        """
        update the request data with job info
        requestData['AgentJobInfo'] = {'vocms234.cern.ch:9999': {"_id":"d1d11dfcb30e0ab47db42007cb6fb847",
        "_rev":"1-8abfaa2de822ed081cb8d174e3e2c003",
        "status":{"inWMBS":334,"success":381,"submitted":{"retry":2,"pending":2},"failure":{"exception":3}},
        "agent_team":"testbed-integration","workflow":"amaltaro_OracleUpgrade_TEST_HG1401_140220_090116_6731",
        "timestamp":1394738860,"sites":{"T2_CH_CERN_AI":{"submitted":{"retry":1,"pending":1}},
        "T2_CH_CERN":{"success":6,"submitted":{"retry":1,"pending":1}},
        "T2_DE_DESY":{"failure":{"exception":3},"success":375}},
        "agent":"WMAgentCommissioning",
        "tasks":
           {"/amaltaro_OracleUpgrade_TEST_HG1401_140220_090116_6731/Production":
            {"status":{"failure":{"exception":3},"success":331},
             "sites":{"T2_DE_DESY": {"success":325,"wrappedTotalJobTime":11305908,
                                     "dataset":{},"failure":{"exception":3},
                                     "cmsRunCPUPerformance":{"totalJobCPU":10869688.8,
                                                             "totalEventCPU":10832426.7,
                                                             "totalJobTime":11255865.9},
                                     "inputEvents":0},
                      "T2_CH_CERN":{"success":6,"wrappedTotalJobTime":176573,
                                    "dataset":{},
                                    "cmsRunCPUPerformance":{"totalJobCPU":167324.8,
                                                            "totalEventCPU":166652.1,
                                                            "totalJobTime":174975.7},
                                    "inputEvents":0}},
             "subscription_status":{"updated":1393108089, "finished":2, "total":2,"open":0},
             "jobtype":"Production"},
            "/amaltaro_OracleUpgrade_TEST_HG1401_140220_090116_6731/Production/ProductionMergeRAWSIMoutput/ProductionRAWSIMoutputMergeLogCollect":
             {"jobtype":"LogCollect",
              "subscription_status":{"updated":1392885768,
              "finished":0,
              "total":1,"open":1}},
            "/amaltaro_OracleUpgrade_TEST_HG1401_140220_090116_6731/Production/ProductionMergeRAWSIMoutput":
              {"status":{"success":41,"submitted":{"retry":1,"pending":1}},
                "sites":{"T2_DE_DESY":{"datasetStat":{"totalLumis":973,"events":97300,"size":105698406915},
                                       "success":41,"wrappedTotalJobTime":9190,
                                       "dataset":{"/GluGluToHTohhTo4B_mH-350_mh-125_8TeV-pythia6-tauola/Summer12-OracleUpgrade_TEST_ALAN_HG1401-v1/GEN-SIM":
                                                   {"totalLumis":973,"events":97300,"size":105698406915}},
                                       "cmsRunCPUPerformance":{"totalJobCPU":548.92532,"totalEventCPU":27.449808,"totalJobTime":2909.92125},
                                    "inputEvents":97300},
                         "T2_CH_CERN":{"submitted":{"retry":1,"pending":1}}},
                "subscription_status":{"updated":1392885768,"finished":0,"total":1,"open":1},
                "jobtype":"Merge"},
           "agent_url":"vocms231.cern.ch:9999",
           "type":"agent_request"}}
        """
        if jobData:
            for row in jobData["rows"]:
                # condition checks if documents are deleted between calls.
                # just ignore in that case
                if row["doc"]:
                    jobInfo = requestData[row["doc"]["workflow"]]
                    jobInfo.setdefault("AgentJobInfo", {})
                    jobInfo["AgentJobInfo"][row["doc"]["agent_url"]] = row["doc"]

    def _getRequestAndAgent(self, filterRequest=None):
        """
        returns the [['request_name', 'agent_url'], ....]
        """
        options = {}
        options["reduce"] = True
        options["group"] = True
        result = self._getCouchView("requestAgentUrl", options)

        if filterRequest == None:
            keys = [row['key'] for row in result["rows"]]
        else:
            keys = [row['key'] for row in result["rows"] if row['key'][0] in filterRequest]
        return keys

    def _getLatestJobInfo(self, keys):
        """
        keys is [['request_name', 'agent_url'], ....]
        returns ids
        """
        if len(keys) == 0:
            return []
        options = {}
        options["reduce"] = True
        options["group"] = True
        result = self._getCouchView("latestRequest", options, keys)
        ids = [row['value']['id'] for row in result["rows"]]
        return ids

    def _getAllDocsByIDs(self, ids, include_docs=True):
        """
        keys is [id, ....]
        returns document
        """
        if len(ids) == 0:
            return None
        options = {}
        options["include_docs"] = include_docs
        result = self.couchDB.allDocs(options, ids)

        return result

    def _getAgentInfo(self):
        """
        returns all the agents status on wmstats
        """
        options = {}
        result = self._getCouchView("agentInfo", options)

        return result

    def agentsByTeam(self, filterDrain=False):
        """
        return a dictionary like {team:#agents,...}
        """
        result = self._getAgentInfo()
        response = dict()

        for agentInfo in result["rows"]:
            #filtering empty string
            orgteams = agentInfo['value']['agent_team'].split(',')
            teams = [t for t in orgteams if t]
            for team in teams:
                response.setdefault(team, 0)

            if filterDrain:
                if not agentInfo['value'].get('drain_mode', False):
                    for team in teams:
                        response[team] += 1
            else:
                for team in teams:
                    response[team] += 1
        return response

    def getServerInstance(self):
        return self.couchServer

    def getDBInstance(self):
        return self.couchDB

    def getRequestDBInstance(self):
        return self.reqDB

    def getHeartbeat(self):
        try:
            return self.couchDB.info()
        except Exception as ex:
            return {'error_message': str(ex)}

    def getRequestByNames(self, requestNames, jobInfoFlag=False):
        """
        To use this function reqDBURL need to be set when wmstats initialized.
        This will be deplicated so please don use this.
        """
        requestInfo = self.reqDB.getRequestByNames(requestNames, True)

        if jobInfoFlag:
            # get request and agent info
            self._updateRequestInfoWithJobInfo(requestInfo)
        return requestInfo

    def getActiveData(self, jobInfoFlag=False):

        return self.getRequestByStatus(WMStatsReader.ACTIVE_STATUS, jobInfoFlag)

    def getT0ActiveData(self, jobInfoFlag=False):

        return self.getRequestByStatus(WMStatsReader.T0_ACTIVE_STATUS, jobInfoFlag)

    def getRequestByStatus(self, statusList, jobInfoFlag=False, limit=None, skip=None,
                           legacyFormat=False):

        """
        To use this function reqDBURL need to be set when wmstats initialized.
        This will be deplicated so please don use this.
        If legacyFormat is True convert data to old wmstats format from current reqmgr format.
        Shouldn't be set to True unless existing code breaks
        """

        requestInfo = self.reqDB.getRequestByStatus(statusList, True, limit, skip)

        if legacyFormat:
            # convert the format to wmstas old format
            for requestName, doc in requestInfo.items():
                requestInfo[requestName] = convertToLegacyFormat(doc)

        if jobInfoFlag:
            # get request and agent info
            self._updateRequestInfoWithJobInfo(requestInfo)
        return requestInfo

    def getRequestSummaryWithJobInfo(self, requestName):
        """
        get request info with job status
        """
        requestInfo = self.reqDB.getRequestByNames(requestName)
        self._updateRequestInfoWithJobInfo(requestInfo)
        return requestInfo

    def getArchivedRequests(self):
        """
        get list of archived workflow in wmstats db.
        """

        options = {"group_level": 1, "reduce": True}

        results = self.couchDB.loadView(self.couchapp, "allWorkflows", options=options)['rows']
        requestNames = [x['key'] for x in results]

        workflowDict = self.reqDB.getStatusAndTypeByRequest(requestNames)
        archivedRequests = []
        for request, value in workflowDict.items():
            if value[0].endswith("-archived"):
                archivedRequests.append(request)

        return archivedRequests

    def isWorkflowCompletedWithLogCollectAndCleanUp(self, requestName):
        """
        check whether workflow  is completed including LogCollect and CleanUp tasks
        TODO: If the parent task all failed and next task are not created at all,
            It can't detect complete status.
            If the one of the task doesn't contain any jobs, it will return False
        """

        requestInfo = self.getRequestSummaryWithJobInfo(requestName)
        reqInfoInstance = RequestInfo(requestInfo[requestName])
        return reqInfoInstance.isWorkflowFinished()

    def getTaskJobSummaryByRequest(self, requestName, sampleSize=1):

        options = {'reduce': True, 'group_level': 5, 'startkey': [requestName],
                   'endkey': [requestName, {}]}
        results = self.couchDB.loadView(self.couchapp, "jobsByStatusWorkflow", options=options)
        jobDetails = {}
        for row in results['rows']:
            # row["key"] = ['workflow', 'task', 'jobstatus', 'exitCode', 'site']
            startKey = row["key"][:4]
            endKey = []
            site = row["key"][4]
            if site:
                startKey.append(site)

            endKey.extend(startKey)
            endKey.append({})
            numOfError = row["value"]

            jobInfo = self.jobDetailByTasks(startKey, endKey, numOfError, sampleSize)
            jobDetails = nestedDictUpdate(jobDetails, jobInfo)
        return jobDetails

    def jobDetailByTasks(self, startKey, endKey, numOfError, limit=1):
        options = {'include_docs': True, 'reduce': False,
                   'startkey': startKey, 'endkey': endKey,
                   'limit': limit}
        result = self.couchDB.loadView(self.couchapp, "jobsByStatusWorkflow", options=options)
        jobInfoDoc = {}
        for row in result['rows']:
            keys = row['key']
            workflow = keys[0]
            task = keys[1]
            jobStatus = keys[2]
            exitCode = keys[3]
            site = keys[4]

            jobInfoDoc.setdefault(workflow, {})
            jobInfoDoc[workflow].setdefault(task, {})
            jobInfoDoc[workflow][task].setdefault(jobStatus, {})
            jobInfoDoc[workflow][task][jobStatus].setdefault(exitCode, {})
            jobInfoDoc[workflow][task][jobStatus][exitCode].setdefault(site, {})
            finalStruct = jobInfoDoc[workflow][task][jobStatus][exitCode][site]
            finalStruct["errorCount"] = numOfError
            finalStruct.setdefault("samples", [])
            finalStruct["samples"].append(row["doc"])

        return jobInfoDoc
