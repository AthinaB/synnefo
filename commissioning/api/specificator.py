

def shorts(s):
    if not isinstance(s, unicode):
        s = str(s)

    if len(s) <= 64:
        return s

    return s[:61] + '...'
        

class CanonifyException(Exception):
    pass

class SpecifyException(Exception):
    pass


class Canonical(object):
    def __init__(self, *args, **kw):
        self.args = args
        self.kw = kw
        self.name = kw.pop('classname', self.__class__.__name__)
        opts = {}
        for k, v in kw.items():
            if not isinstance(v, Canonical):
                opts[k] = v
                del kw[k]

        self.opts = opts
        self.init()

        if 'default' in opts:
            item = opts['default']
            if item is None:
                opts['null'] = 1
            else:
                opts['default'] = self.call(item)

    def init(self):
        return

    def __call__(self, item):
        opts = self.opts
        if item is None and 'default' in opts:
            item = opts['default']

        can_be_null = opts.get('null', False)
        if item is None and can_be_null:
            return None

        return self.call(item)

    def call(self, item):
        return item

    def tostring(self, depth=0, showopts=0, multiline=0):
        depth += 1
        if not multiline:
            argdepth = ''
            owndepth = ''
            joinchar = ','
            padchar = ''
        else:
            argdepth = '    ' * depth
            owndepth = '    ' * (depth - 1)
            joinchar = ',\n'
            padchar = '\n'

        args = [a.tostring( depth=depth,
                            showopts=showopts,
                            multiline=multiline) for a in self.args]
        args += [("%s=%s" %
                    (k, v.tostring( depth=depth,
                                    showopts=showopts,
                                    multiline=multiline)))
                                    
                                    for k, v in self.kw.items()]
        if showopts:
            args += [("%s=%s" % (k, str(v))) for k, v in self.opts.items()]

        if len(args) == 0:
            string = "%s(%s)" % (self.name, ','.join(args))
        else:
            string = "%s(%s" % (self.name, padchar)
            for arg in args:
                string += argdepth + arg + joinchar
            string = string[:-1] + padchar
            string += owndepth + ")"

        return string

    __str__ = tostring

    def __repr__(self):
        return self.tostring(multiline=0, showopts=1)

    def call(item):
        canonified = item
        return canonified


class Null(Canonical):

    def call(self, item):
        return None

Nothing = Null()

class Integer(Canonical):

    def call(self, item):
        try:
            num = int(item)
        except ValueError, e:
            try:
                num = int(item, 16)
            except Exception:
                m = "%s: cannot convert '%s' to int" % (self, item)
                raise CanonifyException(m)

        optget = self.opts.get
        minimum = optget('minimum', None)
        maximum = optget('maximum', None)

        if minimum is not None and num < minimum:
            m = "%s: %d < minimum=%d" % (self, num, minimum)
            raise CanonifyException(m)

        if maximum is not None and num > maximum:
            m = "%s: %d > maximum=%d" % (self, num, maximum)
            raise CanonifyException(m)

        return num


class String(Canonical):

    re = None
    matcher = None
    choices = None

    def init(self):
        opts = self.opts
        if 'regex' in opts:
            pat = opts['regex']
            re = self.re
            if re is None:
                import re
                self.re = re

            self.matcher = re.compile(pat, re.UNICODE)
            self.pat = pat

        if 'choices' in opts:
            opts['choices'] = dict((unicode(x), unicode(x))
                                    for x in opts['choices'])

    def call(self, item):
        if not isinstance(item, unicode):
            # require non-unicode items to be utf8
            item = str(item)
            try:
                item = item.decode('utf8')
            except UnicodeDecodeError, e:
                item = item.decode('latin1')
                m = "%s: non-unicode '%s' is not utf8" % (self, shorts(item))
                raise CanonifyException(m)

        opts = self.opts
        if 'choices' in opts:
            choices = opts['choices']
            try:
                unknown = item not in choices
            except TypeError, e:
                m = "%s: unhashable type '%s'" % (self.name, shorts(item))
                raise CanonifyException(m, e)

            if unknown:
                m = "%s: '%s' not in choices" % (self.name, shorts(item))
                raise CanonifyException(m)

            return choices[item]

        optget = opts.get
        itemlen = len(item)
        maxlen = optget('maxlen', None)
        if maxlen is not None and itemlen > maxlen:
            m = "%s: len('%s') > maxlen=%d" % (self, shorts(item), maxlen)
            raise CanonifyException(m)

        minlen = optget('minlen', None)
        if minlen is not None and itemlen < minlen:
            m = "%s: len('%s') < minlen=%d" % (self, shorts(item), minlen)
            raise CanonifyException(m)
            
        matcher = self.matcher
        if matcher is not None:
            match = matcher.match(item)
            if  (       match is None
                    or  (match.start(), match.end()) != (0, itemlen)    ):

                    m = ("%s: '%s' does not match '%s'"
                            % (self, shorts(item), self.pat))
                    raise CanonifyException(m)

        return item


class ListOf(Canonical):

    def init(self):
        args = self.args
        kw = self.kw

        if not (args or kw):
            raise SpecifyException("ListOf requires one or more arguments")

        if args and kw:
            m = ("ListOf requires either positional "
                 "or keyword arguments, but not both")
            raise SpecifyException(m)

        if args:
            if len(args) > 1:
                self.canonical = Tuple(*args)
            else:
                self.canonical = args[0]
        else:
            self.canonical = Args(**kw)

    def call(self, item):
        if item is None:
            item = ()

        try:
            items = iter(item)
        except TypeError, e:
            m = "%s: %s is not iterable" % (self, item)
            raise CanonifyException(m)

        canonical = self.canonical
        canonified = []
        append = canonified.append

        for item in items:
            item = canonical(item)
            append(item)

        if not canonified and self.opts.get('nonempty', False):
            m = "%s: must be nonempty" % (self,)
            raise CanonifyException(m)

        return canonified


class Args(Canonical):

    def init(self):
        if self.args:
            raise ValueError("Args accepts only keyword arguments")

    def call(self, item):
        try:
            item = dict(item)
        except TypeError, e:
            m = "%s: %s is not dict-able" % (self, item)
            raise CanonifyException(m)

        canonified = {}

        try:
            for n, c in self.kw.items():
                canonified[n] = c(item[n])
        except KeyError:
            m = "%s: Argument '%s' not found in '%s'" % (self, shorts(n), shorts(item))
            raise CanonifyException(m)

        return canonified


class Tuple(Canonical):

    def call(self, item):
        try:
            items = list(item)
        except TypeError, e:
            m = "%s: %s is not iterable" % (self, item)
            raise CanonifyException(m)

        canonicals = self.args
        zi = len(items)
        zc = len(canonicals)

        if zi != zc:
            m = "%s: expecting %d elements, not %d (%s)" % (self, zc, zi, str(items))
            raise CanonifyException(m)

        g = (canonical(element) for canonical, element in zip(self.args, item))

        return tuple(g)

    def __add__(self, other):
        oargs = other.args if isinstance(other, Tuple) else (other,)
        args = self.args + oargs
        return self.__class__(*args)


class Dict(Canonical):

    def init(self):
        canonical = {}
        for arg in self.args:
            canonical.update(arg)

        self.canonical = canonical

    def call(self, item):

        try:
            item = dict(item)
        except TypeError:
            m = "%s: '%s' is not dict-able" % (self, shorts(item))
            raise CanonifyException(m)

        canonified = {}
        for n, c in self.canonical:
            canonified[n] = c(item[n])   

        return canonified


class Canonifier(object):
    def __init__(self, name, input_canonicals, output_canonicals):
        self.name = name
        self.input_canonicals = dict(input_canonicals)
        self.output_canonicals = dict(output_canonicals)

    def call_names(self):
        return self.input_canonicals.keys()

    def input_canonical(self, name):
        input_canonicals = self.input_canonicals
        if name not in input_canonicals:
            m = "%s: Invalid input call '%s'" % (self.name, name)
            raise CanonifyException(m)

        return input_canonicals[name]

    def canonify_input(self, name, the_input):
        return self.input_canonical(name)(the_input)

    def output_canonical(self, name):
        output_canonicals = self.output_canonicals
        if name not in output_canonicals:
            m = "%s: Output canonical '%s' does not exist" % (self.name, name)
            raise CanonifyException(m)

        return output_canonicals[name]

    def canonify_output(self, name, the_output):
        return self.output_canonical(name)(the_output)


class Specificator(object):

    def __new__(cls):
        if cls is Specificator:
            m = "Specificator classes must be subclassed"
            raise SpecifyException(m)

        import inspect

        canonical_inputs = {}
        canonical_outputs = {}

        for name in dir(cls):
            f = getattr(cls, name)
            if not inspect.ismethod(f) or f.__name__.startswith('_'):
                continue

            argspec = inspect.getargspec(f)
            defaults = argspec.defaults
            args = argspec.args
            if args and args[0] == 'self':
                args = args[1:]

            if not defaults:
                defaults = ()

            arglen = len(args)
            deflen = len(defaults)

            if arglen != deflen:
                a = (f.__name__, args[:arglen-deflen])
                m = "Unspecified arguments in '%s': %s" % a
                raise SpecifyException(m)

            args = dict(zip(args, defaults))
            for a, c in args.items():
                if not isinstance(c, Canonical):
                    m = ("argument '%s=%s' is not an instance of 'Canonical'"
                         % (a, repr(c)))
                    raise SpecifyException(m)

            canonical = Null() if len(args) == 0 else Args(**args)
            canonical_inputs[name] = canonical

            self = object.__new__(cls)
            canonical = f(self)
            if not isinstance(canonical, Canonical):
                m = "method '%s' does not return a Canonical" % (name,)
                raise SpecifyException(m)
            canonical_outputs[name] = canonical

        return Canonifier(cls.__name__, canonical_inputs, canonical_outputs)

    def __call__(self):
        return self

