import { Document, UserProfile, SearchResponse } from '@/types';

export const mockUser: UserProfile = {
  id: 'u1',
  name: 'Luna Chen',
  firstName: 'Luna',
  email: 'l.chen@deloitte.com',
  department: 'Consulting',
  title: 'Senior Consultant',
  avatarUrl: undefined,
};

export const mockPinnedDocuments: Document[] = [
  {
    id: 'p1',
    name: 'Project Pitch',
    fileType: 'pptx',
    editedAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    isPinned: true,
    author: 'Luna Chen',
  },
  {
    id: 'p2',
    name: 'Timeline',
    fileType: 'docx',
    editedAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    isPinned: true,
    author: 'Marcus Webb',
  },
  {
    id: 'p3',
    name: 'Transportation Audit',
    fileType: 'pdf',
    editedAt: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
    isPinned: true,
    author: 'Sara Kim',
  },
  {
    id: 'p4',
    name: 'Q3 Healthcare Deck',
    fileType: 'pptx',
    editedAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    isPinned: true,
    author: 'Luna Chen',
  },
];

export const mockRecentDocuments: Document[] = [
  {
    id: 'r1',
    name: 'Project Pitch',
    fileType: 'pptx',
    editedAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    isPinned: false,
    author: 'Luna Chen',
  },
  {
    id: 'r2',
    name: 'Timeline',
    fileType: 'docx',
    editedAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    isPinned: false,
    author: 'Marcus Webb',
  },
  {
    id: 'r3',
    name: 'Transportation Audit',
    fileType: 'pdf',
    editedAt: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
    isPinned: false,
    author: 'Sara Kim',
  },
  {
    id: 'r4',
    name: 'Timeline',
    fileType: 'docx',
    editedAt: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
    isPinned: false,
    author: 'Marcus Webb',
  },
  {
    id: 'r5',
    name: 'Timeline',
    fileType: 'docx',
    editedAt: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
    isPinned: false,
    author: 'James Park',
  },
  {
    id: 'r6',
    name: 'Midterm Presentation',
    fileType: 'pptx',
    editedAt: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
    isPinned: false,
    author: 'Luna Chen',
  },
  {
    id: 'r7',
    name: 'Timeline',
    fileType: 'docx',
    editedAt: new Date(Date.now() - 8 * 60 * 60 * 1000).toISOString(),
    isPinned: false,
    author: 'Marcus Webb',
  },
  {
    id: 'r8',
    name: 'Midterm Presentation',
    fileType: 'pptx',
    editedAt: new Date(Date.now() - 10 * 60 * 60 * 1000).toISOString(),
    isPinned: false,
    author: 'Luna Chen',
  },
  {
    id: 'r9',
    name: 'Transportation Audit',
    fileType: 'pdf',
    editedAt: new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString(),
    isPinned: false,
    author: 'Sara Kim',
  },
  {
    id: 'r10',
    name: 'My Notes',
    fileType: 'docx',
    editedAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    isPinned: false,
    author: 'Luna Chen',
  },
];

export const mockSearchResults: SearchResponse = {
  results: [
    {
      id: 's1',
      name: 'Digital Transformation Client Pitch Deck Q3',
      fileType: 'pptx',
      editedAt: new Date(Date.now() - 3 * 30 * 24 * 60 * 60 * 1000).toISOString(),
      isPinned: false,
      author: 'Luna Chen',
      snippet:
        'This deck outlines a comprehensive digital transformation strategy for our healthcare client, covering cloud migration, process automation, and change management frameworks.',
    },
    {
      id: 's2',
      name: 'Digital Transformation Best Practices 2024',
      fileType: 'pdf',
      editedAt: new Date(Date.now() - 60 * 24 * 60 * 60 * 1000).toISOString(),
      isPinned: false,
      author: 'Marcus Webb',
      snippet:
        'Industry best practices for digital transformation initiatives including stakeholder alignment, technology selection, and measuring ROI across enterprise programs.',
    },
    {
      id: 's3',
      name: 'Client Engagement Framework',
      fileType: 'docx',
      editedAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
      isPinned: false,
      author: 'Sara Kim',
      snippet:
        'A structured framework for managing client relationships and engagement across all phases of a consulting project from discovery through delivery.',
    },
    {
      id: 's4',
      name: 'Q3 Strategy Presentation',
      fileType: 'pptx',
      editedAt: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString(),
      isPinned: false,
      author: 'James Park',
      snippet:
        'Quarterly strategy review presentation covering market positioning, competitive analysis, and growth opportunities for the upcoming fiscal period.',
    },
    {
      id: 's5',
      name: 'Travel Reimbursement Policy',
      fileType: 'pdf',
      editedAt: new Date(Date.now() - 180 * 24 * 60 * 60 * 1000).toISOString(),
      isPinned: false,
      author: 'HR Department',
      snippet:
        'Official company policy for employee travel expense reimbursement, including approved categories, submission deadlines, and approval workflows.',
    },
    {
      id: 's6',
      name: 'Innovation Lab Research Notes',
      fileType: 'docx',
      editedAt: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString(),
      isPinned: false,
      author: 'Luna Chen',
      snippet:
        'Research notes from the Q3 innovation lab sessions exploring emerging technologies and their potential applications within our service delivery model.',
    },
  ],
  totalCount: 6,
};
