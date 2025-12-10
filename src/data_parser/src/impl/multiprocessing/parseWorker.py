import multiprocessing


class ParseWorker(multiprocessing.Process):
    def __init__(self, workQueue, resultQueue):
        multiprocessing.Process.__init__(self)
        self.workQueue = workQueue
        self.resultQueue = resultQueue

    def run(self):
        # This is the method that every process will execute
        while True:
            # Use the queue to get the work from the main process
            work = self.workQueue.get()
            # Is this a finish work?
            if work is None:
                # Finish the process
                self.workQueue.task_done()
                # Put the finish work back in the queue
                self.workQueue.put(None)
                # We are done here
                break
            # Parse the file
            parsedInfo = work()
            # Mark the work as done
            self.workQueue.task_done()
            # Add the result to the result queue
            self.resultQueue.put(parsedInfo)
