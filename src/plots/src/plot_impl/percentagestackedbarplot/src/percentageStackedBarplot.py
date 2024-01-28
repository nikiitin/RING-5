from src.plots.src.plot_impl.stackedbarplot.src.stackedBarplot import StackedBarplot
class PercentageStackedBarplot(StackedBarplot):
    
    def _prepareScriptCall(self) -> None:
        # TODO: description file for locations
        # (Avoid hardcoding paths)
        self._RScriptCall = ["./src/plots/src/plot_impl/percentagestackedbarplot/src/run.R"]
        self._RScriptCall.extend(self._preparePlotInfo())
        self._RScriptCall.extend(self._preparePlotStyleInfo())
        print(self._RScriptCall)

    def __call__(self) -> None:
        super().__call__()
        