from builtins import range
import reportlab.graphics.shapes as shapes

def computeRectIntersection(r0, r1):
    """ r0 and r1 specified as tuples of (x0, y0, x1, y1)
         returns an intersecting rectangle in the form of (x0,y0,x1,y1) or None if no intersection
    """
    def _isInRange(n, rangeMin, rangeMax):
        return n >= rangeMin and n <= rangeMax

    if _isInRange(r0[0], r1[0], r1[2]):
        x0 = r0[0]
    elif _isInRange(r1[0], r0[0], r0[2]):
        x0 = r1[0]
    else:
        return None

    if _isInRange(r0[1], r1[1], r1[3]):
        y0 = r0[1]
    elif _isInRange(r1[1], r0[1], r0[3]):
        y0 = r1[1]
    else:
        return None

    if _isInRange(r0[2], r1[0], r1[2]):
        x1 = r0[2]
    elif _isInRange(r1[2], r0[0], r0[2]):
        x1 = r1[2]
    else:
        return None

    if _isInRange(r0[3], r1[1], r1[3]):
        y1 = r0[3]
    elif _isInRange(r1[3], r0[1], r0[3]):
        y1 = r1[3]
    else:
        return None
    
    if y1-y0 == 0 or x1-x0 == 0:
        return None 

    return (x0, y0, x1, y1)

def translateTransform(tx, ty):
    return {"transform":"translate", "tx":tx, "ty":ty}

def scaleTransform(sx, sy):
    return {"transform":"scale", "sx":sx, "sy":sy}

def rotateTransform(theta, cx, cy):
    return {"transform":"rotate", "cx":cx, "cy":cy, "theta":theta}

class InvalidTransform(Exception):
    def __init__(self, transformName):
        self.transformName = transformName
    def __str__(self):
        if self.transformName != None: 
            return "Unknown transform: %s" % self.transformName
        else:
            return "Transform type not specified"

def computeTransformMatrix(transformList):
    """ compute the transform matrix that is the concatenation of all transforms in the 
        specifed transformList
    """
    transformMatrix = shapes.nullTransform()
    for transform in transformList:
        if not 'transform' in transform:
            raise InvalidTransform()
        if transform['transform'] is 'translate':
            transformMatrix = shapes.mmult(transformMatrix, shapes.translate(transform["tx"], transform["ty"]))
        elif transform['transform'] is 'rotate':
            transformMatrix = shapes.mmult(transformMatrix, shapes.translate(transform['cx'], transform['cy']))
            transformMatrix = shapes.mmult(transformMatrix, shapes.rotate(transform["theta"]))
            transformMatrix = shapes.mmult(transformMatrix, shapes.translate(-1.0 * transform['cx'], -1.0 * transform['cy']))
        elif transform['transform'] is 'scale':
            transformMatrix = shapes.mmult(transformMatrix, shapes.scale(transform['sx'], transform['sy']))
        else:
            raise InvalidTransform(transform['transform'])
    return transformMatrix

if __name__ == '__main__':
    import unittest

    class GraphicsUtilsTest(unittest.TestCase):
        def test_computeRectIntersection(self):
            def _test(r1, r2, expectedIntersection):
                actualIntersection = computeRectIntersection(r1, r2)
                self.assertTupleAlmostEqual(actualIntersection, expectedIntersection)

            r1 = (0, 0, 10, 10)
            r2 = (20, 0, 30, 10)
            r3 = (5, 5, 10, 10)
            r4 = (5, 5, 15, 15)
            r5 = (0, 5, 5, 5)
            r6 = (-5, 5, 5, 5)
            r7 = (-5, -5, 15, 15)
            r8 = (0, 0, 256, 256)
            r9 = (-10, -10, 256, 0)

            # test non-intersection
            _test(r1, r2, None)
            _test(r2, r1, None)
            # test full intersection
            _test(r1, r1, r1)
            # test upper-right corner intersection
            _test(r1, r3, r3)
            _test(r3, r1, r3)
            _test(r1, r4, r3)
            _test(r4, r1, r3)
            # test lower-left corner intersection
            _test(r1, r5, r5)
            _test(r1, r6, r5)
            _test(r5, r1, r5)
            _test(r6, r1, r5)
            # test full inclusion
            _test(r1, r7, r1)
            _test(r7, r1, r1)
            # test where the rectangles are adjacent to each other
            _test(r8, r9, None)


        def test_compute_transform(self):
            test_translation = [{"transform":"translate", "tx":10, "ty": -30}]
            matrix = computeTransformMatrix(test_translation)
            self.assertEquals(matrix, (1, 0, 0, 1, 10, -30))

            test_rotation = [{"transform":"rotate", "theta":90, "cx":0, "cy":10}]
            matrix = computeTransformMatrix(test_rotation)
            self.assertTupleAlmostEqual(matrix, (0, 1, -1, 0, 10, 10))

            test_scale = [{"transform":"scale", "sx":2.0, "sy":3.0}]
            matrix = computeTransformMatrix(test_scale)
            self.assertTupleAlmostEqual(matrix, (2, 0, 0, 3, 0, 0))

            test_multi_transform = [{"transform":"translate", "tx":10, "ty": -30},
                                    {"transform":"rotate", "theta":90, "cx":0, "cy":10}]
            matrix = computeTransformMatrix(test_multi_transform)
            self.assertTupleAlmostEqual(matrix, (0, 1, -1, 0, 20, -20))

            test_multi_transform = [{"transform":"scale", "sx":2.0, "sy":3.0},
                                    {"transform":"translate", "tx":10, "ty": -30},
                                    {"transform":"rotate", "theta":90, "cx":0, "cy":10}]
            matrix = computeTransformMatrix(test_multi_transform)
            self.assertTupleAlmostEqual(matrix, (0, 3, -2, 0, 40, -60))

        def assertTupleAlmostEqual(self, first, second, places=7, msg=None, delta=None):
            if first == None:
                self.assertEquals(first, second)
                return
            self.assertEquals(len(first), len(second), msg=msg)
            for i in range(0, len(first)):
                self.assertAlmostEquals(first[i], second[i], places=places, msg=msg, delta=delta)

    unittest.main()

