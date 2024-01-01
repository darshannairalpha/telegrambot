import Global
import re
import datetime
import Functions
from ujson import load

class Status:
    def __init__ (self, rawSheetStatus, ref):
        self.definiteStatus = ref['definiteStatus']
        self.indefiniteStatus = ref['indefiniteStatus']
        self.moreDominantStatuses = ref['moreDominantStatuses']
        
        self.sheetStatus = re.sub('\s*/\s*', '/', rawSheetStatus.upper().strip())
        self.displayStatus = 'NIL'
        self.category = 'UNKNOWN'
        self.standby = False
        self.duty = False
    
    def Reset(self, rawSheetStatus):
        self.sheetStatus = re.sub('\s*/\s*', '/', rawSheetStatus.upper().strip())
        self.standby = False
        self.duty = False

    def LoadStandbyAndDuty(self):
        if re.search('.{2,}/.{2,}', self.sheetStatus):
            splitSheetStatus = self.sheetStatus.split('/')

            if 'SB' in splitSheetStatus:
                self.standby = True
        else:
            if self.sheetStatus == 'X':
                self.duty = True
            if self.sheetStatus == 'SB':
                self.standby = True

    def LoadFullStatus(self):
        dominantStatus = None

        # if statement does the follwing - examples below:
        # 1. sheetStatus: SB/COURSE                  -> dominantStatus: COURSE                  (sets self.standby = True)
        # 2. sheetStatus: SB/COURSE/MISSILE TRANSFER -> dominantStatus: COURSE/MISSILE TRANSFER (sets self.standby = True)
        # 3. sheetStatus: OFF/COURSE                 -> dominantStatus: OFF                     (NA)
        # 4. sheetStatus: OFF/CCL                    -> dominantStatus: OFF/CCL                 (NA)
        # [does not split U/S and O/S]
        # else statement does the following - examples below:
        # 1. sheetStatus: SB                         -> dominantStatus: SB                      (sets self.standby = True)
        # 2. sheetStatus: X                          -> dominantStatus: X                       (sets self.duty = True)
        # 3. sheetStatus: ANYTHING                   -> dominantStatus: ANYTHING                (NA)
        if re.search('.{2,}/.{2,}', self.sheetStatus):
            splitSheetStatus = self.sheetStatus.split('/')

            if 'SB' in splitSheetStatus:
                self.standby = True
                splitSheetStatus.remove('SB')
            
            moreDominantStatus = [x for x in splitSheetStatus if x in self.moreDominantStatuses]
            if moreDominantStatus:
                dominantStatus = '/'.join(moreDominantStatus)
            else:
                dominantStatus = '/'.join(splitSheetStatus)
        else:
            if self.sheetStatus == 'X':
                self.duty = True
            if self.sheetStatus == 'SB':
                self.standby = True
            
            dominantStatus = self.sheetStatus
        
        # if   --- dominantStatus in definite_status.json - displayStatus and category are set
        # else --- searches indefinite_status.json
        #    if   --- keywords in indefinite_status.json - displayStatus = dominantStatus and category is set
        #    else --- NA                                 - displayStatus = dominantStatus (category remains as UNKNOWN)
        displayCategory = self.definiteStatus.get(dominantStatus)
        if displayCategory:
            self.displayStatus = displayCategory['displayStatus']
            self.category = displayCategory['category']
        else:
            for category in self.indefiniteStatus:
                if re.search('|'.join(self.indefiniteStatus[category]), dominantStatus):
                    self.displayStatus = dominantStatus
                    self.category = category
                    return
            
            self.displayStatus = dominantStatus

class Person:
    def __init__(self, flight, person, rawSheetStatus, ref):
        self.flight = flight
        self.rankINT = person['rankINT']
        self.sheetName = person['sheetName']
        self.nor = person['nor']
        self.status = Status(rawSheetStatus, ref)
        self.displayNoStatus = person['displayNoStatus']

        self.displayFull = self.displayNoStatus
    
    def __repr__(self):
        return self.displayNoStatus

    def __CategoriseBottom(self, bottomCategorised):
        if self.status.duty:
            bottomCategorised['dutyPersonnel'].append(self)
        if self.status.standby:
            bottomCategorised['standbyPersonnel'].append(self)
        if self.status.sheetStatus == 'SITE VCOMM':
            bottomCategorised['siteVcomm'] = self.displayNoStatus

    def __CategoriseFull(self, categorisedPersonnel, bottomCategorised):
        if self.flight == 'alpha':
            categorisedPersonnel[self.status.category].append(self)
        
        self.__CategoriseBottom(bottomCategorised)

    def LoadStandbyAndDuty(self, bottomCategorised):
        self.status.LoadStandbyAndDuty()

        self.__CategoriseBottom(bottomCategorised)
    
    def LoadFullStatus(self, categorisedPersonnel, bottomCategorised):
        self.status.LoadFullStatus()
        
        if self.status.displayStatus != 'NIL':
            self.displayFull += ' ' + f'({self.status.displayStatus})'
        
        self.__CategoriseFull(categorisedPersonnel, bottomCategorised)

class DataManager:
    def __init__(self, chatID=None):
        self.fullPS = True
        self.dateDT = None
        self.dateRAW = None
        self.day = None
        self.WCrange = [0, 1, 2]
        self.meDF = None
        self.adwDF = None

        self.personnel = []
        self.categorisedPersonnel = {}
        self.bottomCategorised = {'dutyPersonnel': [], 'standbyPersonnel': [], 'siteVcomm': 'UNKNOWN', 'weaponControllers': []}

        self.ref = {}

        fileName = [
            'callsign',
            'definiteStatus',
            'indefiniteStatus',
            'moreDominantStatuses',
            'psCategories',
            'mergedCells',
            'psOverride',
            'rations',
            'username'
        ]

        filePath = [
            'data/reference/callsign_ref.json',
            'data/reference/definite_status.json',
            'data/reference/indefinite_status.json',
            'data/reference/more_dominant_status.json',
            'data/reference/parade_state_categories.json',
            'data/override/merged_cells.json',
            'data/override/parade_state_override.json',
            'data/override/rations.json',
            'data/reference/username_ref.json'
        ]

        for name, path in zip(fileName, filePath):
            with open(path) as file:
                self.ref[name] = load(file)
        
        for category in self.ref['psCategories']:
            self.categorisedPersonnel[category] = []
        
        if self.ref['username'].get(str(chatID)):
            self.cos = self.ref['username'][str(chatID)]['cos']
        else:
            self.cos = ''
    
    def __SetDate(self, date):
        if isinstance(date, str):
            self.dateRAW = date
            self.dateDT = Functions.DateConverter(date)
        elif isinstance(date, datetime.datetime):
            self.dateDT = date
            self.dateRAW = Functions.DateConverter(date)
        else:
            return ValueError

        self.day = int(self.dateDT.strftime('%#d'))
        self.meDF = Functions.OpenSheet(self.dateDT, 'me')
        self.adwDF = Functions.OpenSheet(self.dateDT, 'adw')

    def __LoadME(self, nameStatus):
        for x in range(Global.TOP, Global.MIDDLE):
            if self.meDF.iloc[x, 0] != 'NIL':
                nameStatus[self.meDF.iloc[x, 0].upper().strip()] = self.meDF.iloc[x, self.day]
    
    def __GetCommSec(self):
        csToDisplay = Functions.ObtainMap('commSec', 'displayNoStatus')

        for x in range(Global.MIDDLE, Global.BOTTOM):
            if self.meDF.iloc[x, self.day].upper().strip() == 'C':
                self.bottomCategorised['commSec'] = csToDisplay.get(self.meDF.iloc[x, 0].upper().strip(), 'UNKNOWN')
                return
        
        self.bottomCategorised['commSec'] = 'UNKNOWN'

    def __GetWeaponControllers(self):
        for x in self.WCrange:
            self.bottomCategorised['weaponControllers'].append(self.adwDF.iloc[x, self.day + 1].upper().strip())
    
    def __SplitCallsigns(self, deltaDay: int):
        temp = []

        # places those on duty(A2(D) to G4) the previous day/on the day into a list
        # splitting ones with multiple callsigns into seperate items
        for x in [self.adwDF.iloc[x, self.day + deltaDay].upper().strip() for x in range(3)]:
            if '/' in x:
                temp.extend(x.split('/'))
            else:
                temp.append(x)
        
        return temp

    def __LoadADW(self, nameStatus):
        self.__GetWeaponControllers()

        # places those on duty the day before into a list and splits those with '/'
        adw_daybefore_list = self.__SplitCallsigns(0)

        # putting all those on duty the day before on changeover
        for x in adw_daybefore_list:
            for callsign in self.ref['callsign']:
                if callsign in x:
                    nameStatus[self.ref['callsign'][callsign]] = '\\'
                    break

        # places those on duty into a list and splits those with '/'
        adw_day_list = self.__SplitCallsigns(1)

        # if (R) present, status is R
        # else status is HFD
        for x in adw_day_list:
            for callsign in self.ref['callsign']:
                if callsign in x:
                    if "(R)" in x:
                        nameStatus[self.ref['callsign'][callsign]]  = "R"
                    else:
                        nameStatus[self.ref['callsign'][callsign]]  = "HFD"
                    break
    
    def __LoadOverrideLists(self, nameStatus):
        for x in self.ref['mergedCells'] + self.ref['psOverride']:
            if Functions.DateConverter(x['startDate']) <= self.dateDT <= Functions.DateConverter(x['endDate']):
                nameStatus[x['sheetName']] = x['sheetStatus']

    def __LoadSheetStatus(self, date):
        self.__SetDate(date)

        nameStatus = {}
        self.__LoadME(nameStatus)
        if self.fullPS:
            self.__LoadADW(nameStatus)
        else:
            self.__GetWeaponControllers()
        self.__LoadOverrideLists(nameStatus)

        return nameStatus
    
    def __SortStandbyAndDuty(self):
        self.bottomCategorised['dutyPersonnel'] = sorted(self.bottomCategorised['dutyPersonnel'], key=lambda x: x.rankINT, reverse=True)
        self.bottomCategorised['standbyPersonnel'] = sorted(self.bottomCategorised['standbyPersonnel'], key=lambda x: x.rankINT, reverse=True)

        rankRef = {"duty": [[9, 12], [4, 9], [1, 9], [1, 9], [1, 3], [1, 3]], "standby": [[9, 12], [1, 9], [1, 3]]}

        dutyPersonnelNew = ['UNKNOWN' for x in range(6)]
        dutyOpenSlots = [x for x in range(6)]
        for personnel in self.bottomCategorised['dutyPersonnel']:
            add = False
            for i in dutyOpenSlots:
                if personnel.rankINT in range(rankRef['duty'][i][0], rankRef['duty'][i][1]):
                    if i == 0:
                        add = True
                    if i in [1, 2, 3] and personnel.nor == 'REGULAR':
                        add = True
                    if i in [4, 5] and personnel.nor == 'NSF':
                        add = True

                    if add:
                        dutyOpenSlots.remove(i)
                        dutyPersonnelNew[i] = personnel.displayNoStatus
                        break
        
        self.bottomCategorised['dutyPersonnel'] = dutyPersonnelNew

        standbyPersonnelNew = ['UNKNOWN' for x in range(3)]
        standbyOpenSlots = [x for x in range(3)]
        for personnel in self.bottomCategorised['standbyPersonnel']:
            add = False
            for i in standbyOpenSlots:
                if personnel.rankINT in range(rankRef['standby'][i][0], rankRef['standby'][i][1]):
                    if i == 0:
                        add = True
                    if i == 1 and personnel.nor == 'REGULAR':
                        add = True
                    if i == 2 and personnel.nor == 'NSF':
                        add = True

                    if add:
                        standbyOpenSlots.remove(i)
                        standbyPersonnelNew[i] = personnel.displayNoStatus
                        break
        
        self.bottomCategorised['standbyPersonnel'] = standbyPersonnelNew

    def __LoadAll(self, date, WCstandby=False):
        if WCstandby:
            self.WCrange = [0, 1, 2, 4, 5, 6]
        nameStatus = self.__LoadSheetStatus(date)

        for flight in ['alpha', 'bravo', 'others']:
            with open(f'data/personnel/{flight}.json') as flightJson:
                flightList = load(flightJson)
        
            for person in flightList:
                self.personnel.append(Person(flight, person, nameStatus.get(person['sheetName'], 'UNKNOWN'), self.ref))

                if self.fullPS:
                    if person['sheetName'] in self.ref['callsign'].values() and not person['sheetName'] in nameStatus:
                        self.personnel[-1].status.sheetStatus = 'NIL'
                    
                    self.personnel[-1].LoadFullStatus(self.categorisedPersonnel, self.bottomCategorised)
                
                else:
                    self.personnel[-1].LoadStandbyAndDuty(self.bottomCategorised)

        self.__SortStandbyAndDuty()
    
    def __Update(self, date):
        self.bottomCategorised = {'dutyPersonnel': [], 'standbyPersonnel': [], 'siteVcomm': 'UNKNOWN', 'weaponControllers': []}

        nameStatus = self.__LoadSheetStatus(date)

        for person in self.personnel:
            person.status.Reset(nameStatus.get(person.sheetName, 'UNKNOWN'))
            person.LoadStandbyAndDuty(self.bottomCategorised)
        
        self.__SortStandbyAndDuty()
    
    def __psTop(self):
        psStr = f'Good Day ALPHA, below is the Forecasted Parade State for {self.dateRAW}.\n\n' \
                f'COS: {self.cos}\n\n' \
                f'TOTAL STRENGTH ({len([x for x in self.personnel if x.flight == "alpha"])})\n\n'
        
        for category in self.categorisedPersonnel:
            if category != 'UNKNOWN':
                psStr += f'{category}: ({len(self.categorisedPersonnel[category])})\n' + \
                    '\n'.join(person.displayFull for person in self.categorisedPersonnel[category]) + '\n\n'

        return psStr + '---------------------------------------------------\n\n'
    
    def __psMiddle(self):
        if self.dateRAW in self.ref['rations']:
            rationNum = self.ref['rations'][self.dateRAW]
        else:
            rationNum = self.ref['rations']['everyday']

        midStr = ''

        if rationNum[0] != 0:
            midStr += f'BREAKFAST: [{rationNum[0]} PAX]\n' \
                f'COS WILL SCAN ON BEHALF OF ALPHA\n\n' \
        
        if rationNum[1] != 0:
            lunchPersonnel = [x for x in self.categorisedPersonnel['PRESENT']]
            lunchPersonnel = sorted(lunchPersonnel, key=lambda x: (x.nor, x.rankINT))
            lunchPersonnel = sorted(lunchPersonnel[:rationNum[1]], key=lambda x: x.rankINT, reverse=True)
            lunchPersonnel = [x.displayNoStatus for x in lunchPersonnel]

            midStr += f'LUNCH: [{rationNum[1]} PAX]\n' \
                + '\n'.join(lunchPersonnel) + '\n\n'

        if rationNum[2] != 0:
            midStr += f'DINNER: [{rationNum[2]} PAX]\n' \
                    f'COS WILL SCAN ON BEHALF OF ALPHA\n\n' \

        if midStr == '':
            return ''
        else:
            return '[RATION SCANNERS]\n\n' + midStr + '---------------------------------------------------\n\n'

    def __psBottom(self):
        return f'[DUTY CREW FOR {self.dateRAW}]\n' \
        f'OSC: {self.bottomCategorised["dutyPersonnel"][0]}\n' \
        f'SSM: {self.bottomCategorised["dutyPersonnel"][1]}\n' \
        f'ADSS: {self.bottomCategorised["dutyPersonnel"][2]}\n' \
        f'ADSS: {self.bottomCategorised["dutyPersonnel"][3]}\n' \
        f'ADWS: {self.bottomCategorised["dutyPersonnel"][4]}\n' \
        f'ADWS: {self.bottomCategorised["dutyPersonnel"][5]}\n\n' \
        f'SITE VCOMM: {self.bottomCategorised["siteVcomm"]}\n\n' \
        f'[STANDBY CREW FOR {self.dateRAW}]\n' \
        f'AWO: {self.bottomCategorised["standbyPersonnel"][0]}\n' \
        f'ADSS: {self.bottomCategorised["standbyPersonnel"][1]}\n' \
        f'ADWS: {self.bottomCategorised["standbyPersonnel"][2]}\n\n' \
        f'G1: {self.bottomCategorised["weaponControllers"][0]}\n' \
        f'G2: {self.bottomCategorised["weaponControllers"][1]}\n' \
        f'G3A: {self.bottomCategorised["weaponControllers"][2]}'
    
    def FullPS(self, date):
        self.fullPS = True
        self.__LoadAll(date)
        return self.__psTop() + self.__psMiddle() + self.__psBottom()
    
    def CombinedBottomPS(self, startDateDT, endDateDT):
        self.fullPS = False
        self.__LoadAll(startDateDT)
        combStr = self.__psBottom()

        while startDateDT < endDateDT:
            startDateDT += datetime.timedelta(days=1)
            self.__Update(startDateDT)
            combStr += '\n\n---------------------------------------------------\n\n' + self.__psBottom()
        
        return combStr
    
    def CombinedDutyForecast(self, startDateDT, endDateDT):
        self.fullPS = False
        beforeDateRAW = Functions.DateConverter(startDateDT - datetime.timedelta(days=1))
        
        self.__LoadAll(startDateDT, True)
        self.__GetCommSec()
        yield self.dateRAW, beforeDateRAW, self.bottomCategorised

        while startDateDT <= endDateDT:
            beforeDateRAW = Functions.DateConverter(startDateDT)
            startDateDT += datetime.timedelta(days=1)
            self.__Update(startDateDT)
            self.__GetCommSec()
            yield self.dateRAW, beforeDateRAW, self.bottomCategorised