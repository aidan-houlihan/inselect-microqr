import unittest
import shutil
import tempfile

from itertools import izip
from pathlib import Path

import numpy as np

import cv2

from inselect.lib.document import InselectImage, InselectDocument
from inselect.lib.document import validate_normalised
from inselect.lib.inselect_error import InselectError
from inselect.lib.rect import Rect


TESTDATA = Path(__file__).parent / 'test_data'


class TestValidateNormalised(unittest.TestCase):
    def test_validate_normalised(self):
        validate_normalised([Rect(0,0,1,1)])
        self.assertRaises(InselectError, validate_normalised, [(-0.1, 0,    1,   1)])
        self.assertRaises(InselectError, validate_normalised, [( 0,  -0.1,  1,   1)])
        self.assertRaises(InselectError, validate_normalised, [( 0,   0,    1.1, 1)])
        self.assertRaises(InselectError, validate_normalised, [( 0,   0,    1,   1.1)])


class TestImage(unittest.TestCase):
    def test_open(self):
        i = InselectImage(TESTDATA / 'test_segment.png')
        self.assertFalse(i._npimage)

    def test_non_existent_file(self):
        self.assertRaises(InselectError, InselectImage, TESTDATA / 'i am not a file.png')

    def test_not_an_image(self):
        f = tempfile.NamedTemporaryFile()
        i = InselectImage(f.name)
        with self.assertRaises(InselectError):
            i.array

    def test_repr(self):
        p = TESTDATA / 'test_segment.png'
        i = InselectImage(p)
        self.assertEqual("InselectImage('{0}')".format(str(p)), repr(i))

    def test_str(self):
        p = TESTDATA / 'test_segment.png'
        i = InselectImage(p)
        self.assertEqual("InselectImage ['{0}'] [Unloaded]".format(str(p)), str(i))
        i.array    # Forces image to be read
        self.assertEqual("InselectImage ['{0}'] [Loaded]".format(str(p)), str(i))

    def test_array(self):
        i = InselectImage(TESTDATA / 'test_segment.png')
        self.assertEqual((437, 459), i.array.shape[:2])

    def test_from_normalised(self):
        i = InselectImage(TESTDATA / 'test_segment.png')
        h,w = i.array.shape[:2]
        boxes = [Rect(0, 0, 1, 1), Rect(0, 0.2, 0.1, 0.8)]
        self.assertEqual([Rect(0, 0, 459, 437), Rect(0, 87, 45, 349)],
                         list(i.from_normalised(boxes)))

    def test_not_normalised(self):
        i = InselectImage(TESTDATA / 'test_segment.png')
        self.assertRaises(i.from_normalised([Rect(0, 0, 2, 2)]))

    def test_to_normalised(self):
        i = InselectImage(TESTDATA / 'test_segment.png')
        boxes = [Rect(0, 0, 459, 437), Rect(0, 0, 153, 23)]
        self.assertEqual([Rect(0, 0, 1, 1), Rect(0, 0, 1.0/3, 1.0/19)],
                         list(i.to_normalised(boxes)))

    def test_validate_in_bounds(self):
        i = InselectImage(TESTDATA / 'test_segment.png')
        self.assertRaises(InselectError, i.validate_in_bounds, [(-1,  0, 459, 437)])
        self.assertRaises(InselectError, i.validate_in_bounds, [( 0, -1, 459, 437)])
        self.assertRaises(InselectError, i.validate_in_bounds, [( 0,  0, 460, 437)])
        self.assertRaises(InselectError, i.validate_in_bounds, [( 0,  0, 459, 438)])

    def test_save_crops(self):
        temp = tempfile.mkdtemp()
        try:
            i = InselectImage(TESTDATA / 'test_segment.png')

            # Entire image
            p = Path(temp) / 'whole.png'
            i.save_crops([Rect(0, 0, 1, 1)], [p])
            self.assertTrue(np.all(i.array==InselectImage(p).array))

            # Subsection of image
            p = Path(temp) / 'partial.png'
            i.save_crops([Rect(0.1, 0.2, 0.4, 0.3)], [p])
            expected = i.array[87:218, 45:228]
            self.assertTrue(np.all(expected==InselectImage(p).array))
        finally:
             shutil.rmtree(temp)


class TestDocument(unittest.TestCase):
    def test_load(self):
        path = TESTDATA / 'test_segment.inselect'
        doc = InselectDocument.load(path)
        self.assertEqual(5, len(doc.items))
        self.assertEqual(doc.scanned.path, path.with_suffix('.png'))
        self.assertTrue(doc.thumbnail is None)

    def test_load_images(self):
        source = TESTDATA / 'test_segment.inselect'
        temp = tempfile.mkdtemp()
        try:
            doc_temp = Path(temp) / 'test_segment.inselect'
            open(str(doc_temp), 'w').write(source.open().read())

            # Document load with no scanned image file
            self.assertRaises(InselectError, InselectDocument.load, doc_temp)

            # Document load with scanned image file present
            scanned_temp = Path(temp) / 'test_segment.png'
            open(str(scanned_temp), 'wb')       # File only needs to exist
            actual  = InselectDocument.load(doc_temp)
            self.assertEqual(InselectDocument.load(source).items, actual.items)
            self.assertFalse(actual.thumbnail)

            # Document load with scanned and thumbnail files present
            thumbnail_temp = Path(temp) / 'test_segment_thumbnail.jpg'
            open(str(thumbnail_temp), 'wb')       # File only needs to exist
            actual  = InselectDocument.load(doc_temp)
            self.assertEqual(InselectDocument.load(source).items, actual.items)
            self.assertTrue(actual.thumbnail)
        finally:
             shutil.rmtree(temp)

    def test_save(self):
        source = TESTDATA / 'test_segment.inselect'
        temp = tempfile.mkdtemp()
        try:
            doc_temp = Path(temp) / 'test_segment.inselect'
            open(str(doc_temp), 'w').write(source.open().read())

            scanned_temp = Path(temp) / 'test_segment.png'
            open(str(scanned_temp), 'wb')       # File only needs to exist

            items = [ {'rect': Rect(0.1, 0.2, 0.5, 0.5) }, ]

            d = InselectDocument.load(doc_temp)
            d.set_items(items)
            d.save()

            self.assertEqual(items, InselectDocument.load(doc_temp).items)
        finally:
             shutil.rmtree(temp)

    def test_repr(self):
        path = TESTDATA / 'test_segment.inselect'
        doc = InselectDocument.load(path)
        expected = "InselectDocument ['{0}'] [5 items]".format(str(doc.scanned.path))
        self.assertEqual(expected, repr(doc))

    def test_save_crops(self):
        path = TESTDATA / 'test_segment.inselect'
        doc = InselectDocument.load(path)

        crops_dir = doc.save_crops()
        try:
            self.assertTrue(crops_dir.is_dir())
            self.assertEqual(5, len(list(crops_dir.glob('*.tiff'))))

            boxes = doc.scanned.from_normalised([i['rect'] for i in doc.items])
            for box,path in izip(boxes, crops_dir.glob('*.tiff')):
                x0, y0, x1, y1 = box.coordinates
                self.assertTrue(np.all(doc.scanned.array[y0:y1, x0:x1] ==
                                       cv2.imread(str(path))))
        finally:
             shutil.rmtree(str(crops_dir))

    def test_set_items(self):
        path = TESTDATA / 'test_segment.inselect'
        doc = InselectDocument.load(path)

        items = [ {'rect': Rect(0, 0, 0.5, 0.5)}, ]
        doc.set_items(items)
        self.assertEqual(items, doc.items)

        # Not normalised
        items = [ {'rect': Rect(0, 0, 1, 2)}, ]
        self.assertRaises(InselectError, doc.set_items, items)


if __name__=='__main__':
    unittest.main()
