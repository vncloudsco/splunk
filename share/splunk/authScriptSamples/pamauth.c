/* Copyright (C) 2004-2007 Philippe Troin <phil@fifi.org>
 * I hereby place this program in the public domain.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <security/pam_appl.h>

struct pam_closure {
  const char *user;
  const char *typed_passwd;
  int   verbose_p;
};

static int
pam_conversation (int nmsgs,
                  const struct pam_message **msg,
                  struct pam_response **resp,
                  void *closure)
{
  int replies = 0;
  struct pam_response *reply = 0;
  struct pam_closure *c = (struct pam_closure *) closure;

  reply = (struct pam_response *) calloc (nmsgs, sizeof (*reply));
  if (!reply) return PAM_CONV_ERR;
	
  for (replies = 0; replies < nmsgs; replies++)
    {
      switch (msg[replies]->msg_style)
        {
        case PAM_PROMPT_ECHO_ON:
          reply[replies].resp_retcode = PAM_SUCCESS;
          reply[replies].resp = strdup (c->user);	   /* freed by PAM */
          if (c->verbose_p)
            fprintf (stderr, "     PAM ECHO_ON(\"%s\") ==> \"%s\"\n",
                     msg[replies]->msg,
                     reply[replies].resp);
          break;
        case PAM_PROMPT_ECHO_OFF:
          reply[replies].resp_retcode = PAM_SUCCESS;
          reply[replies].resp = strdup (c->typed_passwd);   /* freed by PAM */
          if (c->verbose_p)
            fprintf (stderr, "     PAM ECHO_OFF(\"%s\") ==> password\n",
                     msg[replies]->msg);
          break;
        case PAM_TEXT_INFO:
          /* ignore it... */
          reply[replies].resp_retcode = PAM_SUCCESS;
          reply[replies].resp = 0;
          if (c->verbose_p)
            fprintf (stderr, "     PAM TEXT_INFO(\"%s\") ==> ignored\n",
                     msg[replies]->msg);
          break;
        case PAM_ERROR_MSG:
          /* ignore it... */
          reply[replies].resp_retcode = PAM_SUCCESS;
          reply[replies].resp = 0;
          if (c->verbose_p)
            fprintf (stderr, "     PAM ERROR_MSG(\"%s\") ==> ignored\n",
                     msg[replies]->msg);
          break;
        default:
          /* Must be an error of some sort... */
          free (reply);
          if (c->verbose_p)
            fprintf (stderr, "     PAM unknown %d(\"%s\") ==> ignored\n",
                     msg[replies]->msg_style, msg[replies]->msg);
          return PAM_CONV_ERR;
        }
    }
  *resp = reply;
  return PAM_SUCCESS;
}

int
pwvalid (const char* typed_user, const char *typed_passwd, int verbose_p)
{
  const char *service = "pamauth";
  pam_handle_t *pamh = 0;
  int status = -1;
  struct pam_conv pc;
  struct pam_closure c;

  c.user = typed_user;
  c.typed_passwd = typed_passwd;
  c.verbose_p = verbose_p;

  pc.conv = &pam_conversation;
  pc.appdata_ptr = (void *) &c;

  /* Initialize PAM.
   */
  status = pam_start (service, c.user, &pc, &pamh);
  if (verbose_p)
    fprintf (stderr, " pam_start (\"%s\", \"%s\", ...) ==> %d (%s)\n",
             service, c.user,
             status, pam_strerror (pamh, status));
  if (status != PAM_SUCCESS) goto DONE;

  {
    const char *tty = "web";
    status = pam_set_item (pamh, PAM_TTY, strdup(tty));
    if (verbose_p)
      fprintf (stderr, "   pam_set_item (p, PAM_TTY, \"%s\") ==> %d (%s)\n",
               tty, status, pam_strerror(pamh, status));
  }

  status = pam_set_item (pamh, PAM_RUSER, strdup(c.user));
  if (verbose_p)
    fprintf (stderr, "   pam_set_item(p, PAM_RUSER, \"%s\") ==> %d (%s)\n",
             c.user, status, pam_strerror(pamh, status));
  if (status != PAM_SUCCESS) goto DONE;

  pam_fail_delay(pamh, 1);
  status = pam_authenticate (pamh, 0);
  if (verbose_p)
    fprintf (stderr, "   pam_authenticate (...) ==> %d (%s)\n",
             status, pam_strerror(pamh, status));

 DONE:
  if (pamh)
    {
      int status2 = pam_end (pamh, status);
      pamh = 0;
      if (verbose_p)
        fprintf (stderr, " pam_end (...) ==> %d (%s)\n",
                 status2,
                 (status2 == PAM_SUCCESS ? "Success" : "Failure"));
    }
  return (status == PAM_SUCCESS ? 1 : 0);
}

int
main(int argc, char *argv[]) 
{
  static const int bufsize = 1024;
  char password[bufsize];
  int passwordlen;
  /**/
	
fprintf(stderr, "usage:	" );  
if (argc != 2)
    {
      fprintf(stderr, "usage: %s <login>\n", argv[0]);
      return 1;
    }

  if (isatty(fileno(stdin)))
    {
      fprintf(stderr, "%s: cannot be used on a tty\n", argv[0]);
      return 1;
    }

  fgets(password, bufsize, stdin);
  passwordlen = strlen(password);
  if (password[passwordlen-1] == '\n')
    password[passwordlen-1] = 0;

  return pwvalid(argv[1], password, 0) ? 0 : 1;
}

