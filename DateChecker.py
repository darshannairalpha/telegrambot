import datetime
import Functions

def DateCheck(dateRAW):   
    # checks if date provided is 6 digits
    if len(dateRAW) == 6:
        try:
            return Functions.DateConverter(dateRAW)
        except ValueError:
            return

def SingleDate(contArgs):
    if len(contArgs) == 0:
        # no date provided
        dateDT = Functions.CurrentDatetime() + datetime.timedelta(days=1)
        return datetime.datetime(dateDT.year, dateDT.month, dateDT.day)
    elif len(contArgs) == 1:
        return DateCheck(contArgs[0])
    else:
        return

def DoubleDate(contArgs, maxDayDelta:int=None, autofillFirst = True, autofillSecond = True):
    startDateDT = None
    endDateDT = None

    if len(contArgs) == 0:
        if autofillFirst:
            startDateDT = Functions.CurrentDatetime() + datetime.timedelta(days=1)
            startDateDT = datetime.datetime(startDateDT.year, startDateDT.month, startDateDT.day)
            
            endDateDT = startDateDT + datetime.timedelta(days=1)
            endDateDT = datetime.datetime(endDateDT.year, endDateDT.month, endDateDT.day)
    elif len(contArgs) == 1:
        if autofillSecond:
            startDateDT = DateCheck(contArgs[0])
            
            if startDateDT is not None:
                endDateDT = startDateDT + datetime.timedelta(days=1)
    elif len(contArgs) == 2:
        startDateDT = DateCheck(contArgs[0])
        endDateDT = DateCheck(contArgs[1])

        # check if dates are valid
        if startDateDT is None or endDateDT is None:
            startDateDT = None
            endDateDT = None
        else:
            # check if end date is greater than start date
            if startDateDT > endDateDT:
                startDateDT = None
                endDateDT = None
            else:
                if maxDayDelta is not None and (endDateDT - startDateDT).days > maxDayDelta:
                    startDateDT = 'tooFar'
                    endDateDT = None
    
    return startDateDT, endDateDT