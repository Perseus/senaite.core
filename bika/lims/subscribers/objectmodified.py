# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.CORE
#
# Copyright 2018 by it's authors.
# Some rights reserved. See LICENSE.rst, CONTRIBUTORS.rst.

from bika.lims.permissions import ManageLoginDetails
from Products.CMFCore import permissions
from Products.CMFCore.utils import getToolByName


def ObjectModifiedEventHandler(obj, event):
    """ Various types need automation on edit.
    """
    if not hasattr(obj, 'portal_type'):
        return

    if obj.portal_type == 'Calculation':
        pr = getToolByName(obj, 'portal_repository')
        uc = getToolByName(obj, 'uid_catalog')
        obj = uc(UID=obj.UID())[0].getObject()
        version_id = obj.version_id if hasattr(obj, 'version_id') else 0

        backrefs = obj.getBackReferences('MethodCalculation')
        for i, target in enumerate(backrefs):
            target = uc(UID=target.UID())[0].getObject()
            pr.save(obj=target, comment="Calculation updated to version %s" %
                (version_id + 1,))
            reference_versions = getattr(target, 'reference_versions', {})
            reference_versions[obj.UID()] = version_id + 1
            target.reference_versions = reference_versions

    # Note: obj can be also a reference!
    # <Folder at .../client-1/4d1dd3f77b76b3427a005e1f339e7bd4/at_references>
    elif obj.meta_type == obj.portal_type == 'AnalysisRequest':
        mp = obj.manage_permission
        # Allow to remove Analyses / Attachments
        # https://github.com/senaite/senaite.core/issues/780
        can_delete = ["Manager", "LabManager", "Owner"]
        mp(permissions.DeleteObjects, can_delete, 0)

    elif obj.portal_type == 'Contact':
        # Contacts need to be given "Owner" local-role on their Client.
        mp = obj.manage_permission
        mp(permissions.View, ['Manager', 'LabManager', 'LabClerk', 'Owner', 'Analyst', 'Sampler', 'Preserver'], 0)
        mp(permissions.ModifyPortalContent, ['Manager', 'LabManager', 'Owner', 'LabClerk'], 0)
        mp(ManageLoginDetails, ['Manager', 'LabManager', 'LabClerk'], 0)
        # Verify that the Contact details are the same as the Plone user.
        contact_username = obj.Schema()['Username'].get(obj)
        if contact_username:
            contact_email = obj.Schema()['EmailAddress'].get(obj)
            contact_fullname = obj.Schema()['Fullname'].get(obj)
            mt = getToolByName(obj, 'portal_membership')
            member = mt.getMemberById(contact_username)
            if member:
                properties = {'username': contact_username,
                              'email': contact_email,
                              'fullname': contact_fullname}
                member.setMemberProperties(properties)

    elif obj.portal_type == 'AnalysisCategory':
        # If the analysis category's Title is modified, we must
        # re-index all services and analyses that refer to this title.
        for i in [['Analysis', 'bika_analysis_catalog'],
                  ['AnalysisService', 'bika_setup_catalog']]:
            cat = getToolByName(obj, i[1])
            brains = cat(portal_type=i[0], getCategoryUID=obj.UID())
            for brain in brains:
                brain.getObject().reindexObject(idxs=['getCategoryTitle'])
