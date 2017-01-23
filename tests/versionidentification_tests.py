from unittest import TestCase
from unittest.mock import MagicMock, call
from vane.versionidentification import VersionIdentification
import hashlib
from openwebvulndb.common.models import Signature, VersionList, VersionDefinition
from openwebvulndb.common.schemas import VersionListSchema
from os.path import join, dirname


class TestVersionIdentification(TestCase):

    def setUp(self):
        self.versions_list = MagicMock()
        self.hammertime = MagicMock()
        self.version_identification = VersionIdentification(self.hammertime)
        self.version_identification.versions_list = MagicMock()
        self.readme_file = VersionIdentification.File("readme.html", b"This is the readme file.")
        self.style_css_file = VersionIdentification.File("style.css", b"This is the style file.")

    def test_fetch_files_for_version_identification(self):
        self.version_identification.signatures_files = ["readme.html", "style.css", "wp-include/file.js"]
        target = "http://www.target.url/"

        for file in self.version_identification.fetch_files(target):
            pass

        self.hammertime.request.assert_has_calls([call(target + "readme.html"), call(target + "style.css"),
                                                  call(target + "wp-include/file.js")])
        self.hammertime.successful_requests.assert_any_call()

    def test_get_file_hash_return_valid_hash(self):
        expected_file_hash_sha256 = hashlib.sha256(self.readme_file.data).hexdigest()
        expected_file_hash_md5 = hashlib.md5(self.readme_file.data).hexdigest()

        file_hash_sha256 = self.version_identification.get_file_hash(self.readme_file, "sha256")
        file_hash_md5 = self.version_identification.get_file_hash(self.readme_file, "md5")

        self.assertEqual(file_hash_sha256, expected_file_hash_sha256)
        self.assertEqual(file_hash_md5, expected_file_hash_md5)

    def test_file_match_signature(self):
        readme_hash = hashlib.sha256(self.readme_file.data).hexdigest()
        style_css_hash = hashlib.sha256(self.style_css_file.data).hexdigest()
        readme_signature = Signature(path=self.readme_file.name, hash=readme_hash)
        style_css_signature = Signature(path=self.style_css_file.name, hash=style_css_hash)

        self.assertTrue(self.version_identification._file_match_signature(self.readme_file, readme_signature))
        self.assertFalse(self.version_identification._file_match_signature(self.readme_file, style_css_signature))
        self.assertTrue(self.version_identification._file_match_signature(self.style_css_file, style_css_signature))
        self.assertFalse(self.version_identification._file_match_signature(self.style_css_file, readme_signature))

    def test_files_match_version(self):
        style_css_signature = Signature(path="style.css", hash=hashlib.sha256(self.style_css_file.data).hexdigest())
        readme_1_signature = Signature(path="readme.html", hash=hashlib.sha256(b"ReadMe file for 1.0 version.").hexdigest())
        version1_definition = VersionDefinition(version="1.0", signatures=[readme_1_signature, style_css_signature])
        readme_2_signature = Signature(path="readme.html", hash=hashlib.sha256(b"ReadMe file for 2.0 version.").hexdigest())
        version2_definition = VersionDefinition(version="2.0", signatures=[readme_2_signature, style_css_signature])
        readme_file2 = VersionIdentification.File("readme.html", b"ReadMe file for 2.0 version.")
        readme_file1 = VersionIdentification.File("readme.html", b"ReadMe file for 1.0 version.")

        self.assertTrue(self.version_identification._files_match_version([readme_file1, self.style_css_file], version1_definition))
        self.assertTrue(self.version_identification._files_match_version([readme_file2, self.style_css_file], version2_definition))
        self.assertFalse(self.version_identification._files_match_version([readme_file1, self.style_css_file], version2_definition))
        self.assertFalse(self.version_identification._files_match_version([readme_file2, self.style_css_file], version1_definition))

    def test_identify_version(self):
        style_css_signature = Signature(path="style.css", hash=hashlib.sha256(self.style_css_file.data).hexdigest())
        readme_1_signature = Signature(path="readme.html", hash=hashlib.sha256(b"ReadMe file for 1.0 version.").hexdigest())
        version1_definition = VersionDefinition(version="1.0", signatures=[readme_1_signature, style_css_signature])
        readme_2_signature = Signature(path="readme.html", hash=hashlib.sha256(b"ReadMe file for 2.0 version.").hexdigest())
        version2_definition = VersionDefinition(version="2.0", signatures=[readme_2_signature, style_css_signature])
        version_list = VersionList(producer="unittest", key="wordpress", versions=[version1_definition, version2_definition])
        readme_file = VersionIdentification.File("readme.html", b"ReadMe file for 2.0 version.")
        version_identification = VersionIdentification(None)
        version_identification.versions_list = version_list
        version_identification.fetch_files = MagicMock()
        version_identification.fetch_files.return_value = [readme_file, self.style_css_file]

        version = version_identification.identify_version("target")

        self.assertEqual(version, "2.0")

    def test_identify_version_find_closest_match_when_one_file_is_missing(self):
        style_css_signature = Signature(path="style.css", hash=hashlib.sha256(self.style_css_file.data).hexdigest())

        readme_1_signature = Signature(path="readme.html", hash=hashlib.sha256(b"ReadMe file for 1.0 version.").hexdigest())
        file1_signature = Signature(path="file.js", hash=hashlib.sha256(b"file.js for 1.0 version.").hexdigest())
        version1_definition = VersionDefinition(version="1.0", signatures=[readme_1_signature, style_css_signature,
                                                                           file1_signature])

        readme_2_signature = Signature(path="readme.html", hash=hashlib.sha256(b"ReadMe file for 2.0 version.").hexdigest())
        file2_signature = Signature(path="file.js", hash=hashlib.sha256(b"file.js for 2.0 version.").hexdigest())
        version2_definition = VersionDefinition(version="2.0", signatures=[readme_2_signature, style_css_signature,
                                                                           file2_signature])

        version_list = VersionList(producer="unittest", key="wordpress", versions=[version1_definition,
                                                                                   version2_definition])
        file_js = VersionIdentification.File("file.js", b"file.js for 1.0 version.")
        version_identification = VersionIdentification(None)
        version_identification.versions_list = version_list
        version_identification.fetch_files = MagicMock()
        version_identification.fetch_files.return_value = [file_js, self.style_css_file]

        version = version_identification.identify_version("target")

        self.assertEqual(version, "1.0")

    def test_load_versions_signatures(self):
        filename = join(dirname(__file__), "samples/vane2_versions.json")

        self.version_identification.load_versions_signatures(filename)

        self.assertEqual(self.version_identification.versions_list, VersionListSchema().load(
            {"key": "wordpress", "producer": "unittest", "versions": [{"version": "2.0", "signatures":
             [{"path": "file.js", "hash": "1234", "algo": "SHA256"}]}]}).data)
        self.assertEqual(self.version_identification.signatures_files, ["readme.html", "my_file.css", "file.js"])
