## Falafel Balls

This is a recipe for fried Falafel balls.

```python
import math

class MyFalafel(object):
```

Falafel balls require a few different methods. First you need to initialize them with a chosen diameter:

```python
    def __init__(self, diameter):
        self.diameter = diameter
        self.doneness = 0
```

Then you need to fry them the the oil.

```python
    def fry(self, minutes):
        self.doneness += minutes
```

You need to check to see if they're done based on the diameter of the falafel.

```python
    @property
    def done(self):
        if self.doneness == 0:
            return False
        volume = 4 / 3 * math.pi * (self.diameter / 2)**3
        return (volume / self.doneness) > 1
```

Now let's see that whole thing in action.

```python
ball = MyFalafel(5)
print('My falafel is', ball.diameter, 'inches in diameter')
print('Is it done already?', ball.done)
ball.fry(6)
print('Is it done yet?', ball.done)
```

With the output:

```
My falafel is 5 inches in diameter
Is it done already? False
Is it done yet? True
```

And here are some things after the output.

```
This won't be changed.
```

