from . import base


# class JobSchedulerQueue(_BaseJobSchedulerQueue):
class MockQueue(base.BaseJobSchedulerQueue):
    "Mocking JobSchedulerQueue."
    verbose_name = 'Test queue'

    # def __init__(self):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.started_jobs = []
        self.refreshed_jobs = []

    def clear(self):
        """Useful for test cases; clear the internal lists."""
        self.started_jobs.clear()
        self.refreshed_jobs.clear()

    def start_job(self, job):
        self.started_jobs.append(job)
        return False

    def end_job(self, job):
        pass

    def refresh_job(self, job, data):
        self.refreshed_jobs.append((job, data))
        return False

    def get_command(self, timeout):
        pass  # TODO: use in test

    def ping(self):
        pass

    # def pong(self, ping_value):
    def pong(self, ping_cmd):
        pass
