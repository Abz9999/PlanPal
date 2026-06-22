from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def update_parameters(context, **kwargs):
    request = context.request
    output_request = request.GET.copy()
    for parameter, value in kwargs.items():
        output_request[parameter] = value
    return output_request.urlencode()
