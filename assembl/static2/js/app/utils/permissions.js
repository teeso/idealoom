import intersection from 'lodash/intersection';

const Permissions = {
  READ: 'read',
  READ_PUBLIC_CIF: 'read_public_cif',
  SELF_REGISTER: 'self_register',
  ADD_POST: 'add_post',
  EDIT_POST: 'edit_post',
  DELETE_POST: 'delete_post',
  DELETE_MY_POST: 'delete_my_post',
  VOTE: 'vote',
  ADD_EXTRACT: 'add_extract',
  EDIT_EXTRACT: 'edit_extract',
  EDIT_MY_EXTRACT: 'edit_my_extract',
  ADD_IDEA: 'add_idea',
  EDIT_IDEA: 'edit_idea',
  EDIT_SYNTHESIS: 'edit_synthesis',
  SEND_SYNTHESIS: 'send_synthesis',
  ADMIN_DISCUSSION: 'admin_discussion',
  SYSADMIN: 'sysadmin',
  MODERATE_POST: 'moderate_post',
  DISC_STATS: 'discussion_stats',
  EXPORT_EXTERNAL_SOURCE: 'export_post'
};
export default Permissions;

export const expertPermissions = [
  Permissions.ADD_EXTRACT,
  Permissions.EDIT_EXTRACT,
  Permissions.EDIT_MY_EXTRACT,
  Permissions.ADD_IDEA,
  Permissions.EDIT_IDEA,
  Permissions.EDIT_SYNTHESIS,
  Permissions.SEND_SYNTHESIS,
  Permissions.ADMIN_DISCUSSION,
  Permissions.SYSADMIN
];

export const canUseExpertInterface = (permissions) => {
  return intersection([permissions, expertPermissions]).length > 0;
};