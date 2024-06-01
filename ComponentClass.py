import global_values
from SigEntryClass import SigEntry
import re
# import global_values
import logging
# from thefuzz import fuzz

class Component:
    def __init__(self, name, version, data):
        self.name = name
        self.version = version
        self.data = data
        self.sigentry_arr = []
        self.ignore = False
        self.mark_reviewed = False
        self.filter_name = self.filter_name_string(name)
        self.filter_version = self.filter_version_string(version)
        self.sig_match_result = -1
        self.compname_found = False
        self.compver_found = False
        self.reason = 'No Action'
        self.best_sigpath = ''

    def get_compverid(self):
        try:
            return self.data['componentVersion'].split('/')[-1]
        except KeyError:
            return ''

    def add_src(self, src_entry):
        sigentry = SigEntry(src_entry)
        self.sigentry_arr.append(sigentry)

    def get_matchtypes(self):
        try:
            return self.data['matchTypes']
        except KeyError:
            return []

    def is_dependency(self):
        dep_types = ['FILE_DEPENDENCY_DIRECT', 'FILE_DEPENDENCY_TRANSITIVE']
        match_types = self.get_matchtypes()
        for m in dep_types:
            if m in match_types:
                return True
        return False

    def is_signature(self):
        sig_types = ['FILE_EXACT', 'FILE_SOME_FILES_MODIFIED', 'FILE_FILES_ADDED_DELETED_AND_MODIFIED']
        match_types = self.get_matchtypes()
        for m in sig_types:
            if m in match_types:
                return True
        return False

    def is_only_signature(self):
        return (not self.is_dependency() and self.is_signature())

    def set_ignore(self):
        self.ignore = True

    def get_reviewed_status(self):
        try:
            if self.data['reviewStatus'] == 'REVIEWED':
                return True
        except KeyError:
            return False
        return False

    def set_reviewed(self):
        if not self.get_reviewed_status():
            self.mark_reviewed = True
        return

    def is_ignored(self):
        try:
            return self.data['ignored']
        except KeyError:
            return False

    def process_signatures(self):
        all_paths_ignoreable = True
        reason = ''
        for sigentry in self.sigentry_arr:
            ignore, reason = sigentry.filter_folders()
            if not ignore:
                all_paths_ignoreable = False
                break
            else:
                self.sigentry_arr.remove(sigentry)

        if all_paths_ignoreable:
            # Ignore
            reason = f"Mark ignored - {reason}"
            self.reason = reason
            logging.debug(f"- Component {self.filter_name}/{self.version}: {reason}")
            self.set_ignore()
        else:
        #     print(f"NOT Ignoring {self.name}/{self.version}")
            self.sig_match_result = 0
            set_reviewed = False
            for sigentry in self.sigentry_arr:
                compname_found, compver_found,\
                    new_match_result = sigentry.search_component(self.filter_name, self.version)
                logging.debug(f"Compname in path {compname_found}, Version in path {compver_found}, "
                              f"Match result {new_match_result}, Path '{sigentry.path}'")
                if compver_found:
                    self.compver_found = True
                if compname_found:
                    self.compname_found = True
                if global_values.version_match_reqd:
                    if compver_found:
                        set_reviewed = True
                elif compname_found:
                    set_reviewed = True
                if new_match_result > self.sig_match_result:
                    self.sig_match_result = new_match_result
                    self.best_sigpath = sigentry.path
                # print(self.name, self.version, src['commentPath'])
            if set_reviewed:
                if self.compver_found:
                    reason = f"Mark reviewed - Compname & version in path '{self.best_sigpath}', Match result {self.sig_match_result}"
                elif self.compname_found:
                    reason = f"Mark reviewed - Compname in path '{self.best_sigpath}', Match result {self.sig_match_result}"

                self.reason = reason
                logging.debug(f"- Component {self.name}/{self.version}: {reason}")
                self.set_reviewed()

    @staticmethod
    def filter_name_string(name):
        # Remove common words
        # - for, with, in, on,
        # Remove strings in brackets
        # Replace / with space
        ret_name = re.sub(r" for | with | in | on | a |apache ", r" ", name, re.IGNORECASE)
        ret_name = re.sub(r"\(.*\)", r"", ret_name)
        ret_name = re.sub(r"/", r" ", ret_name)
        return ret_name

    @staticmethod
    def filter_version_string(version):
        # Remove +git*
        # Remove -snapshot*
        # Replace / with space
        ret_version = re.sub(r"\+git.*", r"", version, re.IGNORECASE)
        ret_version = re.sub(r"-snapshot.*", r"", ret_version, re.IGNORECASE)
        ret_version = re.sub(r"/", r" ", ret_version)
        return ret_version

    def get_compid(self):
        try:
            compurl = self.data['component']
            return compurl.split('/')[-1]
        except KeyError:
            return ''