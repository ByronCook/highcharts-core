from typing import Optional
from collections import UserDict

from validator_collection import validators, checkers

from highcharts import errors
from highcharts.decorators import class_sensitive
from highcharts.metaclasses import HighchartsMeta
from highcharts.options import HighchartsOptions
from highcharts.utility_classes.javascript_functions import CallbackFunction
from highcharts.js_literal_functions import serialize_to_js_literal
from highcharts.headless_export import ExportServer


class Chart(HighchartsMeta):
    """Python representation of a Highcharts ``Chart`` object."""

    def __init__(self, **kwargs):
        self._callback = None
        self._container = None
        self._options = None
        self._variable_name = None

        self.callback = kwargs.get('callback', None)
        self.container = kwargs.get('container', None)
        self.options = kwargs.get('options', None)
        self.variable_name = kwargs.get('variable_name', None)

    @property
    def callback(self) -> Optional[CallbackFunction]:
        """A (JavaScript) function that is run when the chart has loaded and all external
        images have been loaded. Defaults to :obj:`None <python:None>`.

        .. note::

          Setting this proprety is equivalent to setting a value for
          :meth:`ChartOptions.events.load <highcharts.utility_classes.events.ChartEvents.load>`

        :rtype: :class:`CallbackFunction` or :obj:`None <python:None>`
        """
        return self._callback

    @callback.setter
    @class_sensitive(CallbackFunction)
    def callback(self, value):
        self._callback = value

    @property
    def options(self) -> Optional[HighchartsOptions]:
        """The Python representation of the `Highcharts <https://highcharts.com>`_
        ``options`` `configuration object <https://api.highcharts.com/highcharts/>`_
        Defaults to :obj:`None <python:None>`.

        :rtype: :class:`HighchartsOptions` or :obj:`None <python:None>`
        """
        return self._options

    @options.setter
    @class_sensitive(HighchartsOptions)
    def options(self, value):
        self._options = value

    @property
    def container(self) -> Optional[str]:
        """The ``id`` of the ``<div>`` element in which your Highcharts chart should be
        rendered. Defaults to :obj:`None <python:None>`.

        :rtype: :class:`str <python:str>` or :obj:`None <python:None>`
        """
        return self._container

    @container.setter
    def container(self, value):
        self._container = validators.string(value, allow_empty = True)

    @property
    def variable_name(self) -> Optional[str]:
        """The name given to the (JavaScript) variable to which the (JavaScript) Chart
        instance wil be assigned. Defaults to :obj:`None <python:None>`.

        .. note::

          When the :class:`Chart` object is converted to JavaScript code, the
          (JavaScript) chart instance is assigned to a variable in your JavaScript code.
          In the example code below, the Chart instance is assigned to a ``variable_name``
          of ``chart1``:

          .. code-block:: javascript

            var chart1 = Highcharts.Chart('myTargetDiv', {});

        .. warning::

          If :obj:`None <python:None>`, when converted to a JavaScript literal, the
          :class:`Chart` instance will simply not be assigned to a variable.

        :rtype: :class:`str <python:str>` or :obj:`None <python:None>`
        """
        return self._variable_name

    @variable_name.setter
    def variable_name(self, value):
        self._variable_name = validators.variable_name(value, allow_empty = True)

    @classmethod
    def _get_kwargs_from_dict(cls, as_dict):
        kwargs = {
            'callback': as_dict.get('callback', None),
            'container': as_dict.get('container', None) or as_dict.get('renderTo', None),
            'options': as_dict.get('options', None) or as_dict.get('userOptions', None),
            'variable_name': as_dict.get('variable_name',
                                         None) or as_dict.get('variableName', None)
        }

        return kwargs

    def _to_untrimmed_dict(self, in_cls = None) -> dict:
        untrimmed = {
            'callback': self.callback,
            'container': self.container,
            'userOptions': self.options
        }

        return untrimmed

    def to_js_literal(self,
                      filename = None,
                      encoding = 'utf-8') -> Optional[str]:
        """Return the object represented as a :class:`str <python:str>` containing the
        JavaScript object literal.

        :param filename: The name of a file to which the JavaScript object literal should
          be persisted. Defaults to :obj:`None <python:None>`
        :type filename: Path-like

        :param encoding: The character encoding to apply to the resulting object. Defaults
          to ``'utf-8'``.
        :type encoding: :class:`str <python:str>`

        .. note::

          If :meth:`variable_name <Chart.variable_name>` is set, will render a string as
          a new JavaScript instance invocation in the (pseudo-code) form:

          .. code-block:: javascript

            new VARIABLE_NAME = new Chart(...);

          If :meth:`variable_name <Chart.variable_name>` is not set, will simply return
          the ``new Chart(...)`` portion in the string.

        :rtype: :class:`str <python:str>` or :obj:`None <python:None>`
        """
        if filename:
            filename = validators.path(filename)

        untrimmed = self._to_untrimmed_dict()
        as_dict = {}
        for key in untrimmed:
            item = untrimmed[key]
            serialized = serialize_to_js_literal(item, encoding = encoding)
            if serialized is not None:
                as_dict[key] = serialized

        signature_elements = 0

        container_as_str = ''
        if self.container:
            container_as_str = f"""renderTo = '{self.container}'"""
            signature_elements += 1

        options_as_str = ''
        if self.options:
            options_as_str = self.options.to_js_literal(encoding = encoding)
            options_as_str = f"""options = {options_as_str}"""
            signature_elements += 1

        callback_as_str = ''
        if self.callback:
            callback_as_str = self.callback.to_js_literal(encoding = encoding)
            callback_as_str = f"""callback = {callback_as_str}"""
            signature_elements += 1

        signature = """new Highcharts.chart("""
        if container_as_str:
            signature += container_as_str
            if signature_elements > 1:
                signature += ',\n'
        if options_as_str:
            signature += options_as_str
            if signature_elements > 1:
                signature += ',\n'
        if callback_as_str:
            signature += callback_as_str
        signature += ');'

        prefix = ''
        if self.variable_name:
            prefix = f'var {self.variable_name} = '

        as_str = prefix + signature

        if filename:
            with open(filename, 'w', encoding = encoding) as file_:
                file_.write(as_str)

        return as_str

    def download_chart(self,
                       filename = None,
                       auth_user = None,
                       auth_password = None,
                       timeout = 0.5,
                       server_instance = None,
                       **kwargs):
        """Export a downloaded form of the chart using a Highcharts :term:`Export Server`.

        :param filename: The name of the file where the exported chart should (optionally)
          be persisted. Defaults to :obj:`None <python:None>`.
        :type filename: Path-like or :obj:`None <python:None>`

        :param auth_user: The username to use to authenticate against the
          Export Server, using :term:`basic authentication`. Defaults to
          :obj:`None <python:None>`.
        :type auth_user: :class:`str <python:str>` or :obj:`None <python:None>`

        :param auth_password: The password to use to authenticate against the Export
          Server (using :term:`basic authentication`). Defaults to
          :obj:`None <python:None>`.
        :type auth_password: :class:`str <python:str>` or :obj:`None <python:None>`

        :param timeout: The number of seconds to wait before issuing a timeout error.
          The timeout check is passed if bytes have been received on the socket in less
          than the ``timeout`` value. Defaults to ``0.5``.
        :type timeout: numeric or :obj:`None <python:None>`

        :param server_instance: Provide an already-configured :class:`ExportServer`
          instance to use to programmatically produce the exported chart. Defaults to
          :obj:`None <python:None>`, which causes Highcharts for Python to instantiate
          a new :class:`ExportServer` instance.
        :type server_instance: :class:`ExportServer` or :obj:`None <python:None>`

        .. note::

          All other keyword arguments are as per the :class:`ExportServer` constructor.

        :returns: The exported chart image, either as a :class:`bytes <python:bytes>`
          binary object or as a base-64 encoded string (depending on the ``use_base64``
          keyword argument).
        :rtype: :class:`bytes <python:bytes>` or :class:`str <python:str>`
        """
        if not server_instance:
            return ExportServer.get_chart(filename = filename,
                                          auth_user = auth_user,
                                          auth_password = auth_password,
                                          timeout = timeout,
                                          **kwargs)

        if not isinstance(server_instance, ExportServer):
            raise errors.HighchartsValueError(f'server_instance is expected to be an '
                                              f'ExportServer instance. Was: '
                                              f'{server_instance.__class__.__name__}')

        return server_instance.request_chart(filename = filename,
                                             auth_user = auth_user,
                                             auth_password = auth_password,
                                             timeout = timeout)

    @classmethod
    def _copy_dict_key(cls,
                       key,
                       original,
                       other,
                       overwrite = True,
                       **kwargs):
        """Copies the value of ``key`` from ``original`` to ``other``.

        :param key: The key that is to be copied.
        :type key: :class:`str <python:str>`

        :param original: The original :class:`dict <python:dict>` from which it should
          be copied.
        :type original: :class:`dict <python:dict>`

        :param other: The :class:`dict <python:dict>` to which it should be copied.
        :type other: :class:`dict <python:dict>`

        :returns: The value that should be placed in ``other`` for ``key``.
        """
        preserve_data = kwargs.get('preserve_data', True)

        original_value = original[key]
        other_value = other.get(key, None)

        if key == 'data' and preserve_data:
            return other_value
        elif key == 'points' and preserve_data:
            return other_value
        elif key == 'series' and preserve_data:
            if not other_value:
                return [x for x in original_value]
            if len(other_value) != len(original_value):
                matched_series = []
                new_series = []
                for original_item in original_value:
                    matched = False
                    for other_item in other_value:
                        if checkers.are_dicts_equivalent(original_item, other_item):
                            matched_series.append((original_item, other_item))
                            matched = True
                            break
                    if not matched:
                        new_series.append(original_item)
                updated_series = []
                for items in matched_series:
                    original_item = items[0]
                    other_item = items[1]
                    new_item = {}
                    for subkey in original_item:
                        new_item_value = cls._copy_dict_key(subkey,
                                                            original_item,
                                                            new_item,
                                                            overwrite = overwrite,
                                                            **kwargs)
                        new_item[subkey] = new_item_value
                    updated_series.append(new_item)
                updated_series.extend(new_series)

                return updated_series

        elif isinstance(original_value, (dict, UserDict)):
            new_value = {}
            for subkey in original_value:
                new_key_value = cls._copy_dict_key(subkey,
                                                   original_value,
                                                   other_value,
                                                   overwrite = overwrite,
                                                   **kwargs)
                new_value[subkey] = new_key_value

            return new_value

        elif checkers.is_iterable(original_value,
                                  forbid_literals = (str,
                                                     bytes,
                                                     dict,
                                                     UserDict)):
            if overwrite:
                new_value = [x for x in original_value]

                return new_value
            else:
                return other_value

        elif other_value and not overwrite:
            return other_value
        else:
            return original_value

    def copy(self,
             other,
             overwrite = True,
             **kwargs):
        """Copy the configuration settings from this chart to the ``other`` chart.

        :param other: The target chart to which the properties of this chart should
          be copied. If :obj:`None <python:None>`, will create a new chart and populate
          it with properties copied from ``self``. Defaults to :obj:`None <python:None>`.
        :type other: :class:`Chart`

        :param overwrite: if ``True``, properties in ``other`` that are already set will
          be overwritten by their counterparts in ``self``. Defaults to ``True``.
        :type overwrite: :class:`bool <python:bool>`

        :param preserve_data: If ``True``, will preserve the data values in any
          :term:`series` contained in ``other`` and the configuration of the
          :meth:`options.data <Options.data>` property, but will still copy other
          properties as applicable. If ``False``, will overwrite data in ``other``
          with data from ``self``. Defaults to ``True``.
        :type preserve_data: :class:`bool <python:bool>`

        :param kwargs: Additional keyword arguments. Some special descendents of
          :class:`HighchartsMeta` may have special implementations of this method which
          rely on additional keyword arguments.

        :returns: A mutated version of ``other`` with new property values

        """
        super().copy(other,
                     overwrite = overwrite,
                     **kwargs)
