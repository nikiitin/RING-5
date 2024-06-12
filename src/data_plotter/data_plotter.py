from src.data_plotter.multiprocessing.plotWorkPool import PlotWorkPool
from src.data_plotter.src.plotter_impl.plotWorkImpl import PlotWorkImpl
class dataPlotter:
    def __init__(self, outputPath: str, workCsv:str, plotsJson: dict):
        self._plotsJson = plotsJson
        self._outputPath = outputPath
        self._workCsv = workCsv
        self._plotWorkPool = PlotWorkPool.getInstance()
        if (plotsJson is None):
            raise ValueError("No plots to be processed")
        elif (len(plotsJson) == 0):
            raise ValueError("No plots to be processed")
        
    def __call__(self):
        # Start the pool
        self._plotWorkPool.startPool()
        # Add the work to the pool
        for plot in self._plotsJson:
            # Create the plot work
            work = PlotWorkImpl(self._outputPath, self._workCsv, plot)
            self._plotWorkPool.addWork(work)
        # Finish the job
        self._plotWorkPool.setFinishJob()
        print("All plots processed")
            
        
        