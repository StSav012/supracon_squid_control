# -*- coding: utf-8 -*-

import decimal
import re
import math
from numbers import Real
from typing import Any, Dict, Optional, Sequence, Tuple, TypeVar, Union

from pyqtgraph import SignalProxy, SpinBox, functions as fn
from PySide6 import QtCore, QtGui, QtWidgets

__all__ = ['VerticalSlider', 'SpinSlider']

_T: TypeVar = TypeVar('_T')


def fit_dict(original_dict: Dict[_T, Any], new_keys: Sequence[_T]) -> Dict[_T, Any]:
    return dict((k, v) for k, v in original_dict.items() if k in new_keys)


def map_span(x: Real, x_span: Sequence[Real], new_span: Sequence[Real]) -> float:
    return (x - min(x_span)) / (max(x_span) - min(x_span)) * (max(new_span) - min(new_span)) + min(new_span)


def superscript_number(number: Any) -> str:
    ss_dict: Dict[str, str] = {
        '0': '⁰',
        '1': '¹',
        '2': '²',
        '3': '³',
        '4': '⁴',
        '5': '⁵',
        '6': '⁶',
        '7': '⁷',
        '8': '⁸',
        '9': '⁹',
        '-': '⁻',
        '−': '⁻'
    }
    number = str(number)
    for d in ss_dict:
        number = number.replace(d, ss_dict[d])
    return number


class Scale(QtWidgets.QWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, bounds: Sequence[Real] = (0, 1),
                 fancyMinus: bool = True, **kwargs: Any) -> None:
        super().__init__(parent)
        if len(bounds) != 2:
            raise ValueError('The bounds should be a tuple of two numbers, not %r' % bounds)
        try:
            bounds = tuple(map(float, bounds))
        except ValueError:
            raise ValueError('The bounds should be a tuple of two numbers, not %r' % bounds)

        self.opts: Dict[str, Any] = {
            'bounds': tuple(bounds),
            'int': False,  # Set True to force value to be integer
            'step': 0.01,

            'prefix': '',  # string to be prepended to spin box value
            'suffix': '',
            'siPrefix': False,  # Set to True to display numbers with SI prefix (ie, 100pA instead of 1e-10A)

            'decimals': 6,

            'format': "{prefix}{prefixGap}{scaledValue:.{decimals}g}{suffixGap}{siPrefix}{suffix}",
            'fancyMinus': fancyMinus,
        }
        self.setOpts(**kwargs)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        super().paintEvent(event)

        painter: QtGui.QPainter = QtGui.QPainter(self)
        painter.setPen(self.palette().text().color())

        rect: QtCore.QRect = self.contentsRect()

        font_metrics: QtGui.QFontMetrics = QtGui.QFontMetrics(self.font())
        font_height: int = font_metrics.height()
        tick_length: float = font_metrics.averageCharWidth()

        # calculate the optimal ticks count
        num_ticks: int = rect.height() // font_height // 2
        val: float = (max(self.bounds) - min(self.bounds)) / num_ticks
        exp: int = int(math.floor(math.log10(abs(val)))) if val != 0.0 else 0
        man: float = round(val * math.pow(0.1, exp), self.decimals)
        if man % 1:
            man_res: float = 1 / (man % 1)
            while man_res % 1 and man_res % 2 and man_res % 5:
                num_ticks -= 1
                if num_ticks <= 1:
                    break
                val = (max(self.bounds) - min(self.bounds)) / num_ticks
                exp = int(math.floor(math.log10(abs(val)))) if val != 0.0 else 0
                man = round(val * math.pow(0.1, exp), self.decimals)
                if not man % 1:
                    break
                man_res: float = 1 / (man % 1)

        i: int
        for i in range(num_ticks + 1):
            tick_num: str = self.generateText(map_span(i, (0, num_ticks), self.bounds))
            tick_y: float = rect.height() - ((rect.height() - 1) / num_ticks * i) - 1
            painter.drawLine(QtCore.QPointF(rect.left(), tick_y), QtCore.QPointF(rect.left() + tick_length, tick_y))
            if i == 0:
                pass
            elif i == num_ticks:
                tick_y += font_height / 2
            else:
                tick_y += font_height / 4
            painter.drawText(QtCore.QPointF(2 * tick_length, tick_y), tick_num)
        painter.drawLine(rect.bottomLeft(), rect.topLeft())
        painter.end()

    def setOpts(self, **opts) -> None:
        """Set options affecting the behavior of the widget.

        ============== ========================================================================
        **Arguments:**
        bounds         (min,max) Minimum and maximum values allowed in the SpinBox.
                       Either may be None to leave the value unbounded. By default, values are
                       unbounded.
        suffix         (str) suffix (units) to display after the numerical value. By default,
                       suffix is an empty str.
        siPrefix       (bool) If True, then an SI prefix is automatically prepended
                       to the units and the value is scaled accordingly. For example,
                       if value=0.003 and suffix='V', then the SpinBox will display
                       "300 mV" (but a call to SpinBox.value will still return 0.003). In case
                       the value represents a dimensionless quantity that might span many
                       orders of magnitude, such as a Reynolds number, an SI
                       prefix is allowed with no suffix. Default is False.
        prefix         (str) String to be prepended to the spin box value. Default is an empty string.
        step           (float) The size of a single step. This is used when clicking the up/
                       down arrows, when rolling the mouse wheel, or when pressing
                       keyboard arrows while the widget has keyboard focus. Default is 0.01.
        int            (bool) If True, the value is forced to integer type. Default is False
        decimals       (int) Number of decimal values to display. Default is 6.
        format         (str) Formatting string used to generate the text shown. Formatting is
                       done with ``str.format()`` and makes use of several arguments:

                         * *value* - the unscaled value of the spin box
                         * *prefix* - the prefix string
                         * *prefixGap* - a single space if a prefix is present, or an empty
                           string otherwise
                         * *suffix* - the suffix string
                         * *scaledValue* - the scaled value to use when an SI prefix is present
                         * *siPrefix* - the SI prefix string (if any), or an empty string if
                           this feature has been disabled
                         * *suffixGap* - a single space if a suffix is present, or an empty
                           string otherwise.
        ============== ========================================================================
        """
        # print opts
        for k, v in opts.items():
            if k == 'bounds':
                self.opts['bounds'] = min(v), max(v)
            elif k == 'min':
                self.opts['bounds'] = v, max(self.bounds)
            elif k == 'max':
                self.opts['bounds'] = min(self.bounds), v
            elif k in self.opts:
                self.opts[k] = type(self.opts[k])(v)
            else:
                raise TypeError(f'Invalid keyword argument "{k}"')

        # sanity checks:
        if self.opts['int']:
            self.opts['step'] = round(self.opts.get('step', 1))

        self.update()

    @property
    def bounds(self) -> Tuple[Real, Real]:
        return self.opts['bounds']

    @bounds.setter
    def bounds(self, *args: Union[Tuple[Real, Real], Real]) -> None:
        if len(args) == 1 and isinstance(args[0], Sequence):
            self.opts['bounds'] = min(args[0]), max(args[0])
        elif len(args) == 2:
            self.opts['bounds'] = min(args), max(args)
        else:
            raise ValueError(f'I don not know how to interpret {args}')
        self.update()

    @property
    def step(self) -> float:
        return self.opts['step']

    @step.setter
    def step(self, new_value: float) -> None:
        if new_value > 0.:
            self.opts['step'] = new_value
        else:
            raise ValueError(f'Step should not be {new_value}')
        self.update()

    @property
    def prefix(self):
        """ String to be prepended to the value """
        return self.opts['prefix']

    @prefix.setter
    def prefix(self, new_value):
        """ String to be prepended to the value """
        self.opts['prefix'] = new_value
        self.update()

    @property
    def suffix(self):
        """ Suffix (units) to display after the numerical value """
        return self.opts['suffix']

    @suffix.setter
    def suffix(self, new_value):
        """ Suffix (units) to display after the numerical value """
        self.opts['suffix'] = new_value
        self.update()

    @property
    def siPrefix(self):
        return self.opts['siPrefix']

    @siPrefix.setter
    def siPrefix(self, new_value):
        self.opts['siPrefix'] = new_value
        self.update()

    @property
    def si_prefix(self):
        """
        If True, then an SI prefix is automatically prepended
        to the units and the value is scaled accordingly. For example,
        if value=0.003 and suffix='V', then the ValueLabel will display
        "300 mV" (but ValueLabel.value will still be 0.003). In case
        the value represents a dimensionless quantity that might span many
        orders of magnitude, such as a Reynolds number, an SI
        prefix is allowed with no suffix.
        :return: whether SI suffix is prepended to the unit
        """
        return self.opts['siPrefix']

    @si_prefix.setter
    def si_prefix(self, new_value):
        """
        If True, then an SI prefix is automatically prepended
        to the units and the value is scaled accordingly. For example,
        if value=0.003 and suffix='V', then the ValueLabel will display
        "300 mV" (but ValueLabel.value will still be 0.003). In case
        the value represents a dimensionless quantity that might span many
        orders of magnitude, such as a Reynolds number, an SI
        prefix is allowed with no suffix.
        :param new_value (bool) whether SI suffix is prepended to the unit
        """
        self.opts['siPrefix'] = new_value
        self.update()

    @property
    def decimals(self):
        """ Number of decimal values to display """
        return self.opts['decimals']

    @decimals.setter
    def decimals(self, new_value):
        """ Number of decimal values to display """
        self.opts['decimals'] = new_value
        self.update()

    @property
    def format(self):
        """
        Formatting string used to generate the text shown. Formatting is
        done with ``str.format()`` and makes use of several arguments:

          * *prefix* - the prefix string
          * *prefixGap* - a single space if a prefix is present, or an empty
            string otherwise
          * *value* - the unscaled averaged value of the label
          * *scaledValue* - the scaled value to use when an SI prefix is present
          * *exp* and *mantissa* - the numbers so that value == mantissa * (10 ** exp)
          * *superscriptExp* - *exp* displayed with superscript symbols
          * *suffixGap* - a single space if a suffix is present, or an empty
            string otherwise.
          * *siPrefix* - the SI prefix string (if any), or an empty string if
            this feature has been disabled
          * *suffix* - the suffix string

        :return: the formatting string used to generate the text shown
        """
        return self.opts['format']

    @format.setter
    def format(self, new_value):
        """
        Formatting string used to generate the text shown. Formatting is
        done with ``str.format()`` and makes use of several arguments:

          * *prefix* - the prefix string
          * *prefixGap* - a single space if a prefix is present, or an empty
            string otherwise
          * *value* - the unscaled averaged value of the label
          * *scaledValue* - the scaled value to use when an SI prefix is present
          * *exp* and *mantissa* - the numbers so that value == mantissa * (10 ** exp)
          * *superscriptExp* - *exp* displayed with superscript symbols
          * *suffixGap* - a single space if a suffix is present, or an empty
            string otherwise.
          * *siPrefix* - the SI prefix string (if any), or an empty string if
            this feature has been disabled
          * *suffix* - the suffix string

        :param new_value (str) the formatting string used to generate the text shown
        """
        self.opts['format'] = new_value
        self.update()

    @property
    def formatStr(self):
        """
        Formatting string used to generate the text shown. Formatting is
        done with ``str.format()`` and makes use of several arguments:

          * *prefix* - the prefix string
          * *prefixGap* - a single space if a prefix is present, or an empty
            string otherwise
          * *value* - the unscaled averaged value of the label
          * *scaledValue* - the scaled value to use when an SI prefix is present
          * *exp* and *mantissa* - the numbers so that value == mantissa * (10 ** exp)
          * *superscriptExp* - *exp* displayed with superscript symbols
          * *suffixGap* - a single space if a suffix is present, or an empty
            string otherwise.
          * *siPrefix* - the SI prefix string (if any), or an empty string if
            this feature has been disabled
          * *suffix* - the suffix string

        :return: the formatting string used to generate the text shown
        """
        return self.opts['format']

    @formatStr.setter
    def formatStr(self, new_value):
        """
        Formatting string used to generate the text shown. Formatting is
        done with ``str.format()`` and makes use of several arguments:

          * *prefix* - the prefix string
          * *prefixGap* - a single space if a prefix is present, or an empty
            string otherwise
          * *value* - the unscaled averaged value of the label
          * *scaledValue* - the scaled value to use when an SI prefix is present
          * *exp* and *mantissa* - the numbers so that value == mantissa * (10 ** exp)
          * *superscriptExp* - *exp* displayed with superscript symbols
          * *suffixGap* - a single space if a suffix is present, or an empty
            string otherwise.
          * *siPrefix* - the SI prefix string (if any), or an empty string if
            this feature has been disabled
          * *suffix* - the suffix string

        :param new_value (str) the formatting string used to generate the text shown
        """
        self.opts['format'] = new_value
        self.update()

    @property
    def fancyMinus(self):
        """ Whether to replace '-' with '−' in the label shown """
        return self.opts['fancyMinus']

    @fancyMinus.setter
    def fancyMinus(self, new_value):
        """ Whether to replace '-' with '−' in the label shown """
        self.opts['fancyMinus'] = new_value

    @property
    def fancy_minus(self):
        """ Whether to replace '-' with '−' in the label shown """
        return self.opts['fancyMinus']

    @fancy_minus.setter
    def fancy_minus(self, new_value):
        """ Whether to replace '-' with '−' in the label shown """
        self.opts['fancyMinus'] = new_value

    def generateText(self, val: float) -> str:
        if math.isnan(val):
            return ''

        # format the string
        exp: int = int(math.floor(math.log10(abs(val)))) if val != 0.0 else 0
        man: float = val * math.pow(0.1, exp)
        parts = {'value': val, 'prefix': self.prefix, 'suffix': self.suffix, 'decimals': self.decimals,
                 'exp': exp, 'mantissa': man}
        if 'superscriptExp' in self.formatStr:
            parts['superscriptExp'] = superscript_number(exp)
        if self.siPrefix:
            # SI prefix was requested, so scale the value accordingly
            (s, p) = fn.siScale(val)
            parts.update({'siPrefix': p, 'scaledValue': s * val, 'avgValue': s * val})
        else:
            # no SI prefix/suffix requested; scale is 1
            parts.update({'siPrefix': '', 'scaledValue': val, 'avgValue': val})

        parts['prefixGap'] = ' ' if parts['prefix'] else ''
        parts['suffixGap'] = ' ' if (parts['suffix'] or parts['siPrefix']) else ''

        formatted_value: str = self.formatStr.format(**parts)
        if self.fancyMinus:
            formatted_value = formatted_value.replace('-', '−')
        return formatted_value


class VerticalSlider(QtWidgets.QWidget):
    valueChanged = QtCore.Signal(object)  # (value)  for compatibility with QSlider
    sigValueChanged = QtCore.Signal(object)  # (self)
    sigValueChanging = QtCore.Signal(object, object)  # (self, value)  sent immediately; no delay.

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, bounds: Sequence[Real] = (0, 1), value: float = 0.0,
                 **kwargs: Any) -> None:
        """
        ============== ========================================================================
        **Arguments:**
        parent         Sets the parent widget for this SpinBox (optional). Default is None.
        value          (float/int) initial value. Default is 0.0.
        ============== ========================================================================

        All keyword arguments are passed to :func:`setOpts`.
        """
        super().__init__(parent)
        if len(bounds) != 2:
            raise ValueError('The bounds should be a tuple of two numbers, not %r' % bounds)
        try:
            bounds = tuple(map(float, bounds))
        except ValueError:
            raise ValueError('The bounds should be a tuple of two numbers, not %r' % bounds)

        self.opts: Dict[str, Any] = {
            'bounds': tuple(bounds),
            'int': False,  # Set True to force value to be integer
            'step': 0.01,

            'delay': 0.3,  # delay sending wheel update signals for 300ms
            'delayUntilEditFinished': True,  # do not send signals until text editing has finished
        }
        self._value: float = value
        self._last_value_emitted: float = value

        self._slider: QtWidgets.QSlider = QtWidgets.QSlider(self)
        self._scale: Scale = Scale(self)
        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().addWidget(self._slider)
        self.layout().addWidget(self._scale)
        self.layout().setStretch(1, 1)
        self.layout().setContentsMargins(0, 0, 0, 0)

        self._slider.setRange(0, 1000)
        self._slider.setOrientation(QtCore.Qt.Orientation.Vertical)
        self.proxy = SignalProxy(self.sigValueChanging, slot=self.delayedChange, delay=self.opts['delay'])
        self.setOpts(**kwargs)

    def updatePosition(self) -> None:
        self.setValue(round(map_span(round(self._value / self.step) * self.step,
                                     self.bounds, (self._slider.minimum(), self._slider.maximum()))))

    def delayedChange(self) -> None:
        try:
            if self._value != self._last_value_emitted:  # use fn.eq to handle nan
                self._last_value_emitted = self._value
                self.valueChanged.emit(self._value)
                self.sigValueChanged.emit(self)
        except RuntimeError:
            # This can happen if we try to handle a delayed signal
            # after someone else has already deleted the underlying C++ object.
            pass

    def setValue(self, new_value: float) -> None:
        new_value = round(new_value / self.step) * self.step
        if new_value != self._value:
            self._value = new_value
            self.updatePosition()
            # change will be emitted in 300ms if there are no subsequent changes.
            self.sigValueChanging.emit(self, self._value)

    def setOpts(self, **opts) -> None:
        """Set options affecting the behavior of the widget.

        ============== ========================================================================
        **Arguments:**
        bounds         (min,max) Minimum and maximum values allowed in the SpinBox.
                       Either may be None to leave the value unbounded. By default, values are
                       unbounded.
        suffix         (str) suffix (units) to display after the numerical value. By default,
                       suffix is an empty str.
        siPrefix       (bool) If True, then an SI prefix is automatically prepended
                       to the units and the value is scaled accordingly. For example,
                       if value=0.003 and suffix='V', then the SpinBox will display
                       "300 mV" (but a call to SpinBox.value will still return 0.003). In case
                       the value represents a dimensionless quantity that might span many
                       orders of magnitude, such as a Reynolds number, an SI
                       prefix is allowed with no suffix. Default is False.
        prefix         (str) String to be prepended to the spin box value. Default is an empty string.
        step           (float) The size of a single step. This is used when clicking the up/
                       down arrows, when rolling the mouse wheel, or when pressing
                       keyboard arrows while the widget has keyboard focus. Default is 0.01.
        int            (bool) If True, the value is forced to integer type. Default is False
        decimals       (int) Number of decimal values to display. Default is 6.
        format         (str) Formatting string used to generate the text shown. Formatting is
                       done with ``str.format()`` and makes use of several arguments:

                         * *value* - the unscaled value of the spin box
                         * *prefix* - the prefix string
                         * *prefixGap* - a single space if a prefix is present, or an empty
                           string otherwise
                         * *suffix* - the suffix string
                         * *scaledValue* - the scaled value to use when an SI prefix is present
                         * *siPrefix* - the SI prefix string (if any), or an empty string if
                           this feature has been disabled
                         * *suffixGap* - a single space if a suffix is present, or an empty
                           string otherwise.
        regex          (str or RegexObject) Regular expression used to parse the spinbox text.
                       May contain the following group names:

                       * *number* - matches the numerical portion of the string (mandatory)
                       * *siPrefix* - matches the SI prefix string
                       * *suffix* - matches the suffix string

                       Default is defined in ``pyqtgraph.functions.FLOAT_REGEX``.
        evalFunc       (callable) Fucntion that converts a numerical string to a number,
                       preferrably a Decimal instance. This function handles only the numerical
                       of the text; it does not have access to the suffix or SI prefix.
        compactHeight  (bool) if True, then set the maximum height of the spinbox based on the
                       height of its font. This allows more compact packing on platforms with
                       excessive widget decoration. Default is True.
        ============== ========================================================================
        """
        # print opts
        for k, v in opts.items():
            if k == 'bounds':
                self.opts['bounds'] = min(v), max(v)
                self._scale.opts['bounds'] = self.opts['bounds']
            elif k == 'min':
                self.opts['bounds'] = v, max(self.bounds)
                self._scale.opts['bounds'] = self.opts['bounds']
            elif k == 'max':
                self.opts['bounds'] = min(self.bounds), v
                self._scale.opts['bounds'] = self.opts['bounds']
            elif k == 'value':
                pass  # don't set value until bounds have been set
            elif k in self.opts or k in self._scale.opts:
                if k in self.opts:
                    self.opts[k] = type(self.opts[k])(v)
                if k in self._scale.opts:
                    self._scale.opts[k] = type(self._scale.opts[k])(v)
            else:
                raise TypeError(f'Invalid keyword argument "{k}"')
        if 'value' in opts:
            self.setValue(opts['value'])

        # sanity checks:
        if self.opts['int']:
            self.opts['step'] = round(self.opts.get('step', 1))

        if 'delay' in opts:
            self.proxy.setDelay(opts['delay'])

        self._slider.setTickInterval(round(map_span(self.step, self.bounds,
                                                    (self._slider.minimum(), self._slider.maximum()))))
        self.updatePosition()

    @property
    def bounds(self) -> Tuple[Real, Real]:
        return self.opts['bounds']

    @bounds.setter
    def bounds(self, *args: Union[Tuple[Real, Real], Real]) -> None:
        if len(args) == 1 and isinstance(args[0], Sequence):
            self.opts['bounds'] = min(args[0]), max(args[0])
        elif len(args) == 2:
            self.opts['bounds'] = min(args), max(args)
        else:
            raise ValueError(f'I don not know how to interpret {args}')
        self._scale.bounds = self.bounds
        self.updatePosition()

    @property
    def step(self) -> float:
        return self.opts['step']

    @step.setter
    def step(self, new_value: float) -> None:
        if new_value > 0.:
            self.opts['step'] = new_value
        else:
            raise ValueError(f'Step should not be {new_value}')
        self._scale.step = self.step
        self.updatePosition()

    @property
    def prefix(self):
        """ String to be prepended to the value """
        return self._scale.opts['prefix']

    @prefix.setter
    def prefix(self, new_value):
        """ String to be prepended to the value """
        self._scale.opts['prefix'] = new_value
        self.update()

    @property
    def suffix(self):
        """ Suffix (units) to display after the numerical value """
        return self._scale.opts['suffix']

    @suffix.setter
    def suffix(self, new_value):
        """ Suffix (units) to display after the numerical value """
        self._scale.opts['suffix'] = new_value
        self.update()

    @property
    def siPrefix(self):
        return self._scale.opts['siPrefix']

    @siPrefix.setter
    def siPrefix(self, new_value):
        self._scale.opts['siPrefix'] = new_value
        self.update()

    @property
    def si_prefix(self):
        """
        If True, then an SI prefix is automatically prepended
        to the units and the value is scaled accordingly. For example,
        if value=0.003 and suffix='V', then the ValueLabel will display
        "300 mV" (but ValueLabel.value will still be 0.003). In case
        the value represents a dimensionless quantity that might span many
        orders of magnitude, such as a Reynolds number, an SI
        prefix is allowed with no suffix.
        :return: whether SI suffix is prepended to the unit
        """
        return self._scale.opts['siPrefix']

    @si_prefix.setter
    def si_prefix(self, new_value):
        """
        If True, then an SI prefix is automatically prepended
        to the units and the value is scaled accordingly. For example,
        if value=0.003 and suffix='V', then the ValueLabel will display
        "300 mV" (but ValueLabel.value will still be 0.003). In case
        the value represents a dimensionless quantity that might span many
        orders of magnitude, such as a Reynolds number, an SI
        prefix is allowed with no suffix.
        :param new_value (bool) whether SI suffix is prepended to the unit
        """
        self._scale.opts['siPrefix'] = new_value
        self.update()

    @property
    def decimals(self):
        """ Number of decimal values to display """
        return self._scale.opts['decimals']

    @decimals.setter
    def decimals(self, new_value):
        """ Number of decimal values to display """
        self._scale.opts['decimals'] = new_value
        self.update()

    @property
    def format(self):
        """
        Formatting string used to generate the text shown. Formatting is
        done with ``str.format()`` and makes use of several arguments:

          * *prefix* - the prefix string
          * *prefixGap* - a single space if a prefix is present, or an empty
            string otherwise
          * *value* - the unscaled averaged value of the label
          * *scaledValue* - the scaled value to use when an SI prefix is present
          * *exp* and *mantissa* - the numbers so that value == mantissa * (10 ** exp)
          * *superscriptExp* - *exp* displayed with superscript symbols
          * *suffixGap* - a single space if a suffix is present, or an empty
            string otherwise.
          * *siPrefix* - the SI prefix string (if any), or an empty string if
            this feature has been disabled
          * *suffix* - the suffix string

        :return: the formatting string used to generate the text shown
        """
        return self._scale.opts['format']

    @format.setter
    def format(self, new_value):
        """
        Formatting string used to generate the text shown. Formatting is
        done with ``str.format()`` and makes use of several arguments:

          * *prefix* - the prefix string
          * *prefixGap* - a single space if a prefix is present, or an empty
            string otherwise
          * *value* - the unscaled averaged value of the label
          * *scaledValue* - the scaled value to use when an SI prefix is present
          * *exp* and *mantissa* - the numbers so that value == mantissa * (10 ** exp)
          * *superscriptExp* - *exp* displayed with superscript symbols
          * *suffixGap* - a single space if a suffix is present, or an empty
            string otherwise.
          * *siPrefix* - the SI prefix string (if any), or an empty string if
            this feature has been disabled
          * *suffix* - the suffix string

        :param new_value (str) the formatting string used to generate the text shown
        """
        self._scale.opts['format'] = new_value
        self.update()

    @property
    def formatStr(self):
        """
        Formatting string used to generate the text shown. Formatting is
        done with ``str.format()`` and makes use of several arguments:

          * *prefix* - the prefix string
          * *prefixGap* - a single space if a prefix is present, or an empty
            string otherwise
          * *value* - the unscaled averaged value of the label
          * *scaledValue* - the scaled value to use when an SI prefix is present
          * *exp* and *mantissa* - the numbers so that value == mantissa * (10 ** exp)
          * *superscriptExp* - *exp* displayed with superscript symbols
          * *suffixGap* - a single space if a suffix is present, or an empty
            string otherwise.
          * *siPrefix* - the SI prefix string (if any), or an empty string if
            this feature has been disabled
          * *suffix* - the suffix string

        :return: the formatting string used to generate the text shown
        """
        return self._scale.opts['format']

    @formatStr.setter
    def formatStr(self, new_value):
        """
        Formatting string used to generate the text shown. Formatting is
        done with ``str.format()`` and makes use of several arguments:

          * *prefix* - the prefix string
          * *prefixGap* - a single space if a prefix is present, or an empty
            string otherwise
          * *value* - the unscaled averaged value of the label
          * *scaledValue* - the scaled value to use when an SI prefix is present
          * *exp* and *mantissa* - the numbers so that value == mantissa * (10 ** exp)
          * *superscriptExp* - *exp* displayed with superscript symbols
          * *suffixGap* - a single space if a suffix is present, or an empty
            string otherwise.
          * *siPrefix* - the SI prefix string (if any), or an empty string if
            this feature has been disabled
          * *suffix* - the suffix string

        :param new_value (str) the formatting string used to generate the text shown
        """
        self._scale.opts['format'] = new_value
        self.update()

    @property
    def fancyMinus(self):
        """ Whether to replace '-' with '−' in the label shown """
        return self._scale.opts['fancyMinus']

    @fancyMinus.setter
    def fancyMinus(self, new_value):
        """ Whether to replace '-' with '−' in the label shown """
        self._scale.opts['fancyMinus'] = new_value

    @property
    def fancy_minus(self):
        """ Whether to replace '-' with '−' in the label shown """
        return self._scale.opts['fancyMinus']

    @fancy_minus.setter
    def fancy_minus(self, new_value):
        """ Whether to replace '-' with '−' in the label shown """
        self._scale.opts['fancyMinus'] = new_value


class SpinSlider(QtWidgets.QWidget):
    # There's a PyQt bug that leaks a reference to the
    # QLineEdit returned from QAbstractSpinBox.lineEdit()
    # This makes it possible to crash the entire program 
    # by making accesses to the LineEdit after the spinBox has been deleted.
    # I have no idea how to get around this.

    valueChanged = QtCore.Signal(object)  # (value)  for compatibility with QSpinBox
    sigValueChanged = QtCore.Signal(object)  # (self)
    sigValueChanging = QtCore.Signal(object, object)  # (self, value)  sent immediately; no delay.

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, bounds: Sequence[Real] = (0, 1), value: float = 0.0,
                 **kwargs: Any) -> None:
        """
        ============== ========================================================================
        **Arguments:**
        parent         Sets the parent widget for this SpinBox (optional). Default is None.
        value          (float/int) initial value. Default is 0.0.
        ============== ========================================================================

        All keyword arguments are passed to :func:`setOpts`.
        """
        super().__init__(parent)
        if len(bounds) != 2:
            raise ValueError('The bounds should be a tuple of two numbers, not %r' % bounds)
        try:
            bounds = tuple(map(float, bounds))
        except ValueError:
            raise ValueError('The bounds should be a tuple of two numbers, not %r' % bounds)

        self.opts = {
            'bounds': bounds,

            'step': decimal.Decimal('0.01'),  # the spinBox steps by 'step' every time

            'int': False,  # Set True to force value to be integer

            'prefix': '',  # string to be prepended to spin box value
            'suffix': '',
            'siPrefix': False,  # Set to True to display numbers with SI prefix (ie, 100pA instead of 1e-10A)

            'delay': 0.3,  # delay sending wheel update signals for 300ms

            'delayUntilEditFinished': True,  # do not send signals until text editing has finished

            'decimals': 6,

            'format': "{prefix}{prefixGap}{scaledValue:.{decimals}g}{suffixGap}{siPrefix}{suffix}",
            'regex': fn.FLOAT_REGEX,

            'compactHeight': False,  # manually remove extra margin outside of text
        }

        self._spin_box: SpinBox = SpinBox(self, value=value)
        self._spin_box.setOpts(**fit_dict(kwargs, self._spin_box.opts))
        self._title: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self._title.setText(kwargs.get('title', ''))
        self._slider: VerticalSlider = VerticalSlider(self, bounds=bounds, value=value)
        self.proxy = SignalProxy(self.sigValueChanging, slot=self.delayedChange, delay=self.opts['delay'])

    def setOpts(self, **opts):
        """Set options affecting the behavior of the SpinBox.

        ============== ========================================================================
        **Arguments:**
        bounds         (min,max) Minimum and maximum values allowed in the SpinBox. 
                       Either may be None to leave the value unbounded. By default, values are
                       unbounded.
        suffix         (str) suffix (units) to display after the numerical value. By default,
                       suffix is an empty str.
        siPrefix       (bool) If True, then an SI prefix is automatically prepended
                       to the units and the value is scaled accordingly. For example,
                       if value=0.003 and suffix='V', then the SpinBox will display
                       "300 mV" (but a call to SpinBox.value will still return 0.003). In case
                       the value represents a dimensionless quantity that might span many
                       orders of magnitude, such as a Reynolds number, an SI
                       prefix is allowed with no suffix. Default is False.
        prefix         (str) String to be prepended to the spin box value. Default is an empty string.
        step           (float) The size of a single step. This is used when clicking the up/
                       down arrows, when rolling the mouse wheel, or when pressing 
                       keyboard arrows while the widget has keyboard focus. Default is 0.01.
        int            (bool) If True, the value is forced to integer type. Default is False
        decimals       (int) Number of decimal values to display. Default is 6.
        format         (str) Formatting string used to generate the text shown. Formatting is
                       done with ``str.format()`` and makes use of several arguments:

                         * *value* - the unscaled value of the spin box
                         * *prefix* - the prefix string
                         * *prefixGap* - a single space if a prefix is present, or an empty
                           string otherwise
                         * *suffix* - the suffix string
                         * *scaledValue* - the scaled value to use when an SI prefix is present
                         * *siPrefix* - the SI prefix string (if any), or an empty string if
                           this feature has been disabled
                         * *suffixGap* - a single space if a suffix is present, or an empty
                           string otherwise.
        regex          (str or RegexObject) Regular expression used to parse the spinbox text.
                       May contain the following group names:

                       * *number* - matches the numerical portion of the string (mandatory)
                       * *siPrefix* - matches the SI prefix string
                       * *suffix* - matches the suffix string

                       Default is defined in ``pyqtgraph.functions.FLOAT_REGEX``.
        evalFunc       (callable) Fucntion that converts a numerical string to a number,
                       preferrably a Decimal instance. This function handles only the numerical
                       of the text; it does not have access to the suffix or SI prefix.
        compactHeight  (bool) if True, then set the maximum height of the spinbox based on the
                       height of its font. This allows more compact packing on platforms with
                       excessive widget decoration. Default is True.
        ============== ========================================================================
        """
        # print opts
        for k, v in opts.items():
            if k == 'bounds':
                self.setMinimum(v[0], update=False)
                self.setMaximum(v[1], update=False)
            elif k == 'min':
                self.setMinimum(v, update=False)
            elif k == 'max':
                self.setMaximum(v, update=False)
            elif k in ['step', 'minStep']:
                self.opts[k] = decimal.Decimal(str(v))
            elif k == 'value':
                pass  # don't set value until bounds have been set
            elif k == 'format':
                self.opts[k] = str(v)
            elif k == 'regex' and isinstance(v, str):
                self.opts[k] = re.compile(v)
            elif k in self.opts:
                self.opts[k] = v
            else:
                raise TypeError("Invalid keyword argument '%s'." % k)
        if 'value' in opts:
            self.setValue(opts['value'])

        # If bounds have changed, update value to match
        if 'bounds' in opts and 'value' not in opts:
            self.setValue()

            # sanity checks:
        if self.opts['int']:
            self.opts['step'] = round(self.opts.get('step', 1))

            if 'minStep' in opts:
                step = opts['minStep']
                if int(step) != step:
                    raise Exception('Integer SpinBox must have integer minStep size.')
            else:
                ms = int(self.opts.get('minStep', 1))
                if ms < 1:
                    ms = 1
                self.opts['minStep'] = ms

            if 'format' not in opts:
                self.opts['format'] = "{prefix}{prefixGap}{value:d}{suffixGap}{suffix}"

        if 'delay' in opts:
            self.proxy.setDelay(opts['delay'])

        self.updateText()

    def setMaximum(self, m, update=True):
        """Set the maximum allowed value (or None for no limit)"""
        if m is not None:
            m = decimal.Decimal(str(m))
        self.opts['bounds'][1] = m
        if update:
            self.setValue()

    def setMinimum(self, m, update=True):
        """Set the minimum allowed value (or None for no limit)"""
        if m is not None:
            m = decimal.Decimal(str(m))
        self.opts['bounds'][0] = m
        if update:
            self.setValue()

    def setPrefix(self, p):
        """Set a string prefix.
        """
        self.setOpts(prefix=p)

    def setRange(self, r0, r1):
        """Set the upper and lower limits for values in the spinbox.
        """
        self.setOpts(bounds=[r0, r1])

    def setProperty(self, prop, val):
        # for QSpinBox compatibility
        if prop == 'value':
            # if type(val) is QtCore.QVariant:
            # val = val.toDouble()[0]
            self.setValue(val)
        else:
            print("Warning: SpinBox.setProperty('%s', ..) not supported." % prop)

    def setSuffix(self, suf):
        """Set the string suffix appended to the spinbox text.
        """
        self.setOpts(suffix=suf)

    def setSingleStep(self, step):
        """Set the step size used when responding to the mouse wheel, arrow
        buttons, or arrow keys.
        """
        self.setOpts(step=step)

    def setDecimals(self, decimals):
        """Set the number of decimals to be displayed when formatting numeric
        values.
        """
        self.setOpts(decimals=decimals)

    def value(self):
        """
        Return the value of this SpinBox.

        """
        if self.opts['int']:
            return int(self.val)
        else:
            return float(self.val)

    def setValue(self, value=None, update=True, delaySignal=False):
        """Set the value of this SpinBox.

        If the value is out of bounds, it will be clipped to the nearest boundary
        or wrapped if wrapping is enabled.

        If the spin is integer type, the value will be coerced to int.
        Returns the actual value set.

        If value is None, then the current value is used (this is for resetting
        the value after bounds, etc. have changed)
        """
        if value is None:
            value = self.value()

        bounded = True
        if not math.isnan(value):
            bounds = self.opts['bounds']
            if bounds[0] is not None and value < bounds[0]:
                bounded = False
                value = bounds[0]
            if bounds[1] is not None and value > bounds[1]:
                bounded = False
                value = bounds[1]

        if self.opts['int']:
            value = int(value)

        if not isinstance(value, decimal.Decimal):
            value = decimal.Decimal(str(value))

        prev, self.val = self.val, value
        changed = not fn.eq(value, prev)  # use fn.eq to handle nan

        if update and (changed or not bounded):
            self.updateText(prev=prev)

        if changed:
            self.sigValueChanging.emit(self, float(
                self.val))  # change will be emitted in 300ms if there are no subsequent changes.
            if not delaySignal:
                self.emitChanged()

        return value

    def emitChanged(self):
        self.lastValEmitted = self.val
        self.valueChanged.emit(float(self.val))
        self.sigValueChanged.emit(self)

    def delayedChange(self):
        try:
            if not fn.eq(self.val, self.lastValEmitted):  # use fn.eq to handle nan
                self.emitChanged()
        except RuntimeError:
            # This can happen if we try to handle a delayed signal
            # after someone else has already deleted the underlying C++ object.
            pass

    def stepEnabled(self):
        return self.StepEnabledFlag.StepUpEnabled | self.StepEnabledFlag.StepDownEnabled
