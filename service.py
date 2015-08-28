#!/usr/bin/env python
import os
import servicemanager
import subprocess
import win32event
import win32service
import win32serviceutil


# This is my base path
BASE_PATH = os.path.dirname(os.path.abspath(__file__))


class QBService(win32serviceutil.ServiceFramework):
    _base_path = BASE_PATH
    _svc_name_ = "quickbooks_desktop_worker"
    _svc_display_name_ = "Quickbooks Desktop Worker"
    _svc_description_ = "Celery worker process celery COM requests"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

    def SvcDoRun(self):
        # start celery worker
        os.chdir(BASE_PATH)
        self.process = subprocess.Popen(
            "celery worker -A tasks -Q quickbooks -f {} --loglevel=info --pool=solo".format(
                os.path.join(BASE_PATH, 'celery.log')
            )
        )
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        # Do the actual stop 
        if self.process:
            self.process.kill()
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)


if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(QBService)
