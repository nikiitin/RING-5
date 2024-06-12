import multiprocessing

class PlotWorker(multiprocessing.Process):
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
            # Do plotting
            try:
                work()
                # Mark the work as done
                self.workQueue.task_done()
                self.resultQueue.put(0)
            except Exception as e:
                print(f"Error in plot worker: {e}")
                # Add the error to the result queue
                self.resultQueue.put(1)