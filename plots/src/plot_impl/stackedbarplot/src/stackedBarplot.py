from plots.src.plot_impl.barplot.src.barplot import Barplot
class StackedBarplot(Barplot):
    
    def _prepareScriptCall(self) -> None:
        # TODO: description file for locations
        # (Avoid hardcoding paths)
        self._RScriptCall = ["./plots/src/plot_impl/stackedbarplot/src/run.R"]
        self._RScriptCall.extend(self._preparePlotInfo())
        self._RScriptCall.extend(self._preparePlotStyleInfo())

    def __call__(self) -> None:
        super().__call__()
        