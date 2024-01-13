from plots.src.plot_impl.stackedbarplot.src.stackedBarplot import StackedBarplot
class GroupedStackedBarplot(StackedBarplot):
    
    def _prepareScriptCall(self) -> None:
        # TODO: description file for locations
        # (Avoid hardcoding paths)
        self._RScriptCall = ["./plots/src/plot_impl/groupedstackedbarplot/src/run.R"]
        self._RScriptCall.extend(self._preparePlotInfo())
        self._RScriptCall.extend(self._preparePlotStyleInfo())
        print(self._RScriptCall)

    def __call__(self) -> None:
        super().__call__()
        