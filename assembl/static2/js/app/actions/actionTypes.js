/* redux action types */
// @flow
export const UPDATE_CONTENT_LOCALE_BY_ID: 'UPDATE_CONTENT_LOCALE_BY_ID' = 'UPDATE_CONTENT_LOCALE_BY_ID';
export const UPDATE_CONTENT_LOCALE_BY_ORIGINAL_LOCALE: 'UPDATE_CONTENT_LOCALE_BY_ORIGINAL_LOCALE' =
  'UPDATE_CONTENT_LOCALE_BY_ORIGINAL_LOCALE';
export const UPDATE_CONTENT_LOCALE: 'UPDATE_CONTENT_LOCALE' = 'UPDATE_CONTENT_LOCALE';
export const CREATE_RESOURCE: 'CREATE_RESOURCE' = 'CREATE_RESOURCE';
export const DELETE_RESOURCE: 'DELETE_RESOURCE' = 'DELETE_RESOURCE';
export const UPDATE_RESOURCE_DOCUMENT: 'UPDATE_RESOURCE_DOCUMENT' = 'UPDATE_RESOURCE_DOCUMENT';
export const UPDATE_RESOURCE_EMBED_CODE: 'UPDATE_RESOURCE_EMBED_CODE' = 'UPDATE_RESOURCE_EMBED_CODE';
export const UPDATE_RESOURCE_IMAGE: 'UPDATE_RESOURCE_IMAGE' = 'UPDATE_RESOURCE_IMAGE';
export const UPDATE_RESOURCE_TEXT: 'UPDATE_RESOURCE_TEXT' = 'UPDATE_RESOURCE_TEXT';
export const UPDATE_RESOURCE_TITLE: 'UPDATE_RESOURCE_TITLE' = 'UPDATE_RESOURCE_TITLE';
export const UPDATE_RESOURCES: 'UPDATE_RESOURCES' = 'UPDATE_RESOURCES';
export const UPDATE_RC_PAGE_TITLE: 'UPDATE_RC_PAGE_TITLE' = 'UPDATE_RC_PAGE_TITLE';
export const UPDATE_RC_HEADER_IMAGE: 'UPDATE_RC_HEADER_IMAGE' = 'UPDATE_RC_HEADER_IMAGE';
export const UPDATE_RC_PAGE: 'UPDATE_RC_PAGE' = 'UPDATE_RC_PAGE';
export const UPDATE_SECTIONS: 'UPDATE_SECTIONS' = 'UPDATE_SECTIONS';
export const UPDATE_SECTION_TITLE: 'UPDATE_SECTION_TITLE' = 'UPDATE_SECTION_TITLE';
export const UPDATE_SECTION_URL: 'UPDATE_SECTION_URL' = 'UPDATE_SECTION_URL';
export const TOGGLE_EXTERNAL_PAGE: 'TOGGLE_EXTERNAL_PAGE' = 'TOGGLE_EXTERNAL_PAGE';
export const CREATE_SECTION: 'CREATE_SECTION' = 'CREATE_SECTION';
export const DELETE_SECTION: 'DELETE_SECTION' = 'DELETE_SECTION';
export const MOVE_UP_SECTION: 'MOVE_UP_SECTION' = 'MOVE_UP_SECTION';
export const MOVE_DOWN_SECTION: 'MOVE_DOWN_SECTION' = 'MOVE_DOWN_SECTION';
export const UPDATE_LEGAL_NOTICE_ENTRY: 'UPDATE_LEGAL_NOTICE_ENTRY' = 'UPDATE_LEGAL_NOTICE_ENTRY';
export const UPDATE_TERMS_AND_CONDITIONS_ENTRY: 'UPDATE_TERMS_AND_CONDITIONS_ENTRY' = 'UPDATE_TERMS_AND_CONDITIONS_ENTRY';
export const UPDATE_LEGAL_NOTICE_AND_TERMS: 'UPDATE_LEGAL_NOTICE_AND_TERMS' = 'UPDATE_LEGAL_NOTICE_AND_TERMS';
export const UPDATE_VOTE_SESSION_PAGE: 'UPDATE_VOTE_SESSION_PAGE' = 'UPDATE_VOTE_SESSION_PAGE';
export const UPDATE_VOTE_SESSION_PAGE_TITLE: 'UPDATE_VOTE_SESSION_PAGE_TITLE' = 'UPDATE_VOTE_SESSION_PAGE_TITLE';
export const UPDATE_VOTE_SESSION_PAGE_SUBTITLE: 'UPDATE_VOTE_SESSION_PAGE_SUBTITLE' = 'UPDATE_VOTE_SESSION_PAGE_SUBTITLE';
export const UPDATE_VOTE_SESSION_PAGE_INSTRUCTIONS_TITLE: 'UPDATE_VOTE_SESSION_PAGE_INSTRUCTIONS_TITLE' =
  'UPDATE_VOTE_SESSION_PAGE_INSTRUCTIONS_TITLE';
export const UPDATE_VOTE_SESSION_PAGE_INSTRUCTIONS_CONTENT: 'UPDATE_VOTE_SESSION_PAGE_INSTRUCTIONS_CONTENT' =
  'UPDATE_VOTE_SESSION_PAGE_INSTRUCTIONS_CONTENT';
export const UPDATE_VOTE_SESSION_PAGE_PROPOSITIONS_TITLE: 'UPDATE_VOTE_SESSION_PAGE_PROPOSITIONS_TITLE' =
  'UPDATE_VOTE_SESSION_PAGE_PROPOSITIONS_TITLE';
export const UPDATE_VOTE_SESSION_PAGE_IMAGE: 'UPDATE_VOTE_SESSION_PAGE_IMAGE' = 'UPDATE_VOTE_SESSION_PAGE_IMAGE';
export const UPDATE_VOTE_MODULES: 'UPDATE_VOTE_MODULES' = 'UPDATE_VOTE_MODULES';
export const CREATE_TOKEN_VOTE_MODULE: 'CREATE_TOKEN_VOTE_MODULE' = 'CREATE_TOKEN_VOTE_MODULE';
export const DELETE_TOKEN_VOTE_MODULE: 'DELETE_TOKEN_VOTE_MODULE' = 'DELETE_TOKEN_VOTE_MODULE';
export const UPDATE_TOKEN_VOTE_INSTRUCTIONS: 'UPDATE_TOKEN_VOTE_INSTRUCTIONS' = 'UPDATE_TOKEN_VOTE_INSTRUCTIONS';
export const CREATE_TOKEN_VOTE_TYPE: 'CREATE_TOKEN_VOTE_TYPE' = 'CREATE_TOKEN_VOTE_TYPE';
export const DELETE_TOKEN_VOTE_TYPE: 'DELETE_TOKEN_VOTE_TYPE' = 'DELETE_TOKEN_VOTE_TYPE';
export const UPDATE_TOKEN_VOTE_EXCLUSIVE: 'UPDATE_TOKEN_VOTE_EXCLUSIVE' = 'UPDATE_TOKEN_VOTE_EXCLUSIVE';
export const UPDATE_TOKEN_VOTE_TYPE_TITLE: 'UPDATE_TOKEN_VOTE_TYPE_TITLE' = 'UPDATE_TOKEN_VOTE_TYPE_TITLE';
export const UPDATE_TOKEN_VOTE_TYPE_COLOR: 'UPDATE_TOKEN_VOTE_TYPE_COLOR' = 'UPDATE_TOKEN_VOTE_TYPE_COLOR';
export const UPDATE_TOKEN_NUMBER: 'UPDATE_TOKEN_NUMBER' = 'UPDATE_TOKEN_NUMBER';

export type UpdateContentLocaleById = {
  type: typeof UPDATE_CONTENT_LOCALE_BY_ID,
  id: string,
  value: string
};

export type UpdateContentLocaleByOriginalLocale = {
  type: typeof UPDATE_CONTENT_LOCALE_BY_ORIGINAL_LOCALE,
  originalLocale: string,
  value: string
};

export type ContentLocaleInfo = {
  contentLocale: string,
  originalLocale: string
};

export type ContentLocaleMapping = {
  [string]: ContentLocaleInfo
};

export type UpdateContentLocale = {
  type: typeof UPDATE_CONTENT_LOCALE,
  data: ContentLocaleMapping
};

export type UpdateRCPageTitle = {
  locale: string,
  value: string,
  type: typeof UPDATE_RC_PAGE_TITLE
};

export type UpdateResourcesCenterHeaderImage = {
  value: File,
  type: typeof UPDATE_RC_HEADER_IMAGE
};

export type UpdateResourcesCenterPage = {
  headerImage: File | null,
  titleEntries: Array<any> // TODO: use type automatically created from flow
};

export type CreateResource = {
  id: string,
  order: number,
  type: typeof CREATE_RESOURCE
};

export type DeleteResource = {
  id: string,
  type: typeof DELETE_RESOURCE
};

export type UpdateResourceDocument = {
  id: string,
  value: string,
  type: typeof UPDATE_RESOURCE_DOCUMENT
};

export type UpdateResourceEmbedCode = {
  id: string,
  value: string,
  type: typeof UPDATE_RESOURCE_EMBED_CODE
};

export type UpdateResourceImage = {
  id: string,
  value: string,
  type: typeof UPDATE_RESOURCE_IMAGE
};

export type UpdateResourceText = {
  id: string,
  locale: string,
  value: string,
  type: typeof UPDATE_RESOURCE_TEXT
};

export type UpdateResourceTitle = {
  id: string,
  locale: string,
  value: string,
  type: typeof UPDATE_RESOURCE_TITLE
};

export type ResourceInfo = {
  id: string
};

export type ResourcesArray = Array<ResourceInfo>;

export type UpdateResources = {
  resources: ResourcesArray,
  type: typeof UPDATE_RESOURCES
};

export type SectionInfo = {
  id: string
};

export type SectionsArray = Array<SectionInfo>;

export type UpdateSections = {
  sections: SectionsArray,
  type: typeof UPDATE_SECTIONS
};

export type UpdateSectionTitle = {
  id: string,
  locale: string,
  value: string,
  type: typeof UPDATE_SECTION_TITLE
};

export type UpdateSectionUrl = {
  id: string,
  value: string,
  type: typeof UPDATE_SECTION_URL
};

export type ToggleExternalPage = {
  id: string,
  type: typeof TOGGLE_EXTERNAL_PAGE
};

export type CreateSection = {
  id: string,
  order: number,
  type: typeof CREATE_SECTION
};

export type DeleteSection = {
  id: string,
  type: typeof DELETE_SECTION
};

export type UpSection = {
  id: string,
  type: typeof MOVE_UP_SECTION
};

export type DownSection = {
  id: string,
  type: typeof MOVE_DOWN_SECTION
};

export type UpdateLegalNoticeEntry = {
  type: typeof UPDATE_LEGAL_NOTICE_ENTRY,
  locale: string,
  value: string
};

export type UpdateTermsAndConditionsEntry = {
  type: typeof UPDATE_TERMS_AND_CONDITIONS_ENTRY,
  locale: string,
  value: string
};

export type UpdateLegalNoticeAndTerms = {
  legalNoticeEntries: Array<LangStringEntryInput>,
  termsAndConditionsEntries: Array<LangStringEntryInput>,
  type: typeof UPDATE_LEGAL_NOTICE_AND_TERMS
};

export type UpdateVoteSessionPageTitle = {
  locale: string,
  value: string,
  type: typeof UPDATE_VOTE_SESSION_PAGE_TITLE
};

export type UpdateVoteSessionPageSubtitle = {
  locale: string,
  value: string,
  type: typeof UPDATE_VOTE_SESSION_PAGE_SUBTITLE
};

export type UpdateVoteSessionPageInstructionsTitle = {
  locale: string,
  value: string,
  type: typeof UPDATE_VOTE_SESSION_PAGE_INSTRUCTIONS_TITLE
};

export type UpdateVoteSessionPageInstructionsContent = {
  locale: string,
  value: string,
  type: typeof UPDATE_VOTE_SESSION_PAGE_INSTRUCTIONS_CONTENT
};

export type UpdateVoteSessionPagePropositionsTitle = {
  locale: string,
  value: string,
  type: typeof UPDATE_VOTE_SESSION_PAGE_PROPOSITIONS_TITLE
};

export type UpdateVoteSessionHeaderImage = {
  value: File,
  type: typeof UPDATE_VOTE_SESSION_PAGE_IMAGE
};

export type UpdateVoteSessionPage = {
  titleEntries: Array<LangStringEntryInput>,
  subTitleEntries: Array<LangStringEntryInput>,
  instructionsSectionTitleEntries: Array<LangStringEntryInput>,
  instructionsSectionContentEntries: Array<LangStringEntryInput>,
  propositionsSectionTitleEntries: Array<LangStringEntryInput>,
  headerImage: File | null,
  type: typeof UPDATE_VOTE_SESSION_PAGE
};

export type ModuleInfo = {
  id: string
};

export type VoteModulesArray = Array<ModuleInfo>;

export type UpdateVoteModules = {
  VoteModules: VoteModulesArray,
  type: typeof UPDATE_VOTE_MODULES
};

export type CreateTokenVoteModule = {
  id: string,
  type: typeof CREATE_TOKEN_VOTE_MODULE
};

export type DeleteTokenVoteModule = {
  id: string,
  type: typeof DELETE_TOKEN_VOTE_MODULE
};

export type UpdateTokenVoteExclusive = {
  id: string,
  value: boolean,
  type: typeof UPDATE_TOKEN_VOTE_EXCLUSIVE
};

export type UpdateTokenVoteInstructions = {
  id: string,
  locale: string,
  value: string,
  type: typeof UPDATE_TOKEN_VOTE_INSTRUCTIONS
};

export type CreateTokenVoteType = {
  id: string,
  parentId: string,
  type: typeof CREATE_TOKEN_VOTE_TYPE
};

export type DeleteTokenVoteType = {
  parentId: string,
  value: number,
  type: typeof DELETE_TOKEN_VOTE_TYPE
};

export type UpdateTokenVoteTypeTitleType = {
  id: string,
  locale: string,
  value: string,
  type: typeof UPDATE_TOKEN_VOTE_TYPE_TITLE
};

export type UpdateTokenNumber = {
  id: string,
  value: number,
  type: typeof UPDATE_TOKEN_NUMBER
};

export type UpdateTokenVoteTypeColor = {
  id: string,
  value: string,
  type: typeof UPDATE_TOKEN_VOTE_TYPE_COLOR
};

type BasicAction = {
  type: string
};

// TODO: create type for all possible action types

type ResourcesCenterActions =
  | UpdateRCPageTitle
  | UpdateResourcesCenterHeaderImage
  | UpdateResourcesCenterPage
  | CreateResource
  | DeleteResource
  | UpdateResourceDocument
  | UpdateResourceEmbedCode
  | UpdateResourceImage
  | UpdateResourceText
  | UpdateResourceTitle
  | UpdateResources;

type LegalNoticeAndTermsActions = UpdateLegalNoticeEntry | UpdateTermsAndConditionsEntry | UpdateLegalNoticeAndTerms;

type SectionActions = CreateSection | DeleteSection | UpSection | DownSection;

type VoteSessionActions =
  | UpdateVoteSessionPageTitle
  | UpdateVoteSessionPageSubtitle
  | UpdateVoteSessionPageInstructionsTitle
  | UpdateVoteSessionPageInstructionsContent
  | UpdateVoteSessionPagePropositionsTitle
  | UpdateVoteSessionHeaderImage
  | UpdateVoteModules
  | CreateTokenVoteModule
  | UpdateTokenVoteInstructions
  | CreateTokenVoteType
  | DeleteTokenVoteType
  | UpdateTokenVoteTypeTitle
  | updateTokenNumber
  | UpdateTokenVoteTypeColor;

export type Action =
  | UpdateContentLocaleById
  | UpdateContentLocaleByOriginalLocale
  | ResourcesCenterActions
  | LegalNoticeAndTermsActions
  | SectionActions
  | VoteSessionActions
  | BasicAction;