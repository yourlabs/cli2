colors = dict(
    cyan='\u001b[38;5;51m',
    cyan1='\u001b[38;5;87m',
    cyan2='\u001b[38;5;123m',
    cyan3='\u001b[38;5;159m',
    blue='\u001b[38;5;33m',
    blue1='\u001b[38;5;69m',
    blue2='\u001b[38;5;75m',
    blue3='\u001b[38;5;81m',
    blue4='\u001b[38;5;111m',
    blue5='\u001b[38;5;27m',
    green='\u001b[38;5;10m',
    green1='\u001b[38;5;2m',
    green2='\u001b[38;5;46m',
    green3='\u001b[38;5;47m',
    green4='\u001b[38;5;48m',
    green5='\u001b[38;5;118m',
    green6='\u001b[38;5;119m',
    green7='\u001b[38;5;120m',
    purple='\u001b[38;5;5m',
    purple1='\u001b[38;5;6m',
    purple2='\u001b[38;5;13m',
    purple3='\u001b[38;5;164m',
    purple4='\u001b[38;5;165m',
    purple5='\u001b[38;5;176m',
    purple6='\u001b[38;5;145m',
    purple7='\u001b[38;5;213m',
    purple8='\u001b[38;5;201m',
    red='\u001b[38;5;1m',
    red1='\u001b[38;5;9m',
    red2='\u001b[38;5;196m',
    red3='\u001b[38;5;160m',
    red4='\u001b[38;5;197m',
    red5='\u001b[38;5;198m',
    red6='\u001b[38;5;199m',
    yellow='\u001b[38;5;226m',
    yellow1='\u001b[38;5;227m',
    yellow2='\u001b[38;5;226m',
    yellow3='\u001b[38;5;229m',
    yellow4='\u001b[38;5;220m',
    yellow5='\u001b[38;5;230m',
    gray='\u001b[38;5;250m',
    gray1='\u001b[38;5;251m',
    gray2='\u001b[38;5;252m',
    gray3='\u001b[38;5;253m',
    gray4='\u001b[38;5;254m',
    gray5='\u001b[38;5;255m',
    gray6='\u001b[38;5;249m',
    pink='\u001b[38;5;199m',
    pink1='\u001b[38;5;198m',
    pink2='\u001b[38;5;197m',
    pink3='\u001b[38;5;200m',
    pink4='\u001b[38;5;201m',
    pink5='\u001b[38;5;207m',
    pink6='\u001b[38;5;213m',
    orange='\u001b[38;5;202m',
    orange1='\u001b[38;5;208m',
    orange2='\u001b[38;5;214m',
    orange3='\u001b[38;5;220m',
    orange4='\u001b[38;5;172m',
    orange5='\u001b[38;5;166m',
    reset='\u001b[0m',
)

colors.update({
    k + 'bold': v.replace('[', '[1;')
    for k, v in colors.items()
})


class Colors:
    def __init__(self, colors):
        for name, value in colors.items():
            setattr(self, name, value)


colors = Colors(colors)
